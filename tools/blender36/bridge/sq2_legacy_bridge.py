"""SQ2 legacy bridge — use 4.5 projects from inside Blender 3.6.

Install into a Blender 3.6 install as ``3.6/scripts/startup/sq2_legacy_bridge.py``
(see tools/blender36/install_bridge.py). Modules under ``scripts/startup`` are
imported at boot, so the handlers below are active without enabling an add-on.

The project rule is that **every file is Blender 4.5 format**:

* a file that is opened is assumed to come from 4.5 and is repaired in place;
* a file that is appended from is assumed to come from 4.5;
* **nothing is left on disk as a 3.6 file**: after every save this module hands
  the written file to a Blender 4.5 binary, which re-saves it in 4.5 format and
  replaces the file 3.6 just wrote.

What 3.6 itself destroys while loading a 4.5 file, and this module restores:

* ``BLENDER_EEVEE_NEXT`` -> ``BLENDER_EEVEE`` (3.6 has no EEVEE Next; the
  engine name silently falls back on load).
* AgX view transform -> Filmic (3.6 has no AgX; it falls back to Standard,
  which looks wrong).

Both names are gone from the datablocks by the time ``load_post`` runs, so the
originals are recovered by scanning the file bytes for the stored strings. The
4.5 names are remembered per scene and written back by the 4.5 step, so a
round trip keeps EEVEE Next and AgX instead of permanently downgrading them.

Data that needs no fixing: Principled v2 sockets are mapped by Blender's own
versioning (Transmission Weight -> Transmission, Coat Weight -> Clearcoat,
Sheen Weight -> Sheen, Specular IOR Level -> Specular, emission colour and
strength), and node types shared with 3.6 survive as-is.

Environment:

* ``BLENDER45_EXE`` — path to the Blender 4.5 ``blender.exe``. When unset, a
  ``blender-4.*`` directory next to the 3.6 install is used.
* ``SQ2_NO_45_SAVE=1`` — leave saves in 3.6 format (diagnostic only).
"""

import json
import os
import platform
import subprocess
import sys
import time

import bpy
from bpy.app.handlers import persistent

BRIDGE_TAG = "SQ2-BRIDGE"

# Version of the build this module runs in (3.6.23 -> (3, 6, 23)).
CURRENT = tuple(bpy.app.version)

ENGINE_MAP = {
    "BLENDER_EEVEE_NEXT": "BLENDER_EEVEE",
}
VIEW_TRANSFORM_MAP = {
    "AgX": "Filmic",
}

KNOWN_36_ENGINES = {
    "BLENDER_EEVEE",
    "BLENDER_WORKBENCH",
    "CYCLES",
}

# 4.5 names seen in the last opened file, per scene, so the 4.5 save step can
# put back what 3.6 had to substitute: {"Scene": {"engine_45": ...}}.
RESTORE = {}

LAST_REPORT = []

# Files Blender writes for itself; converting these to 4.5 would break the
# install (a 4.5 startup.blend cannot be read back by a 3.6 boot).
CONFIG_NAMES = {"startup.blend", "userpref.blend", "quit.blend", "bookmarks.blend"}

_CONVERTING = False
_45_EXE = False  # False = not looked up yet, None = not found.
_SEEN_ENGINE = {}

# Runs inside Blender 4.5; it loads the 3.6 file, restores the names 3.6 could
# not represent, and writes 4.5 format to the temporary output path.
FOUR5_SCRIPT = r'''
import json
import sys

import bpy

args = sys.argv[sys.argv.index("--") + 1:]
out, cfg_path = args[0], args[1]
with open(cfg_path, "r", encoding="utf-8") as handle:
    restore = json.load(handle).get("restore", {})

for scene in bpy.data.scenes:
    want = restore.get(scene.name) or {}
    engine = want.get("engine_45")
    if engine and scene.render.engine == want.get("engine_36"):
        try:
            scene.render.engine = engine
        except Exception as exc:  # enum gone in a newer 4.x
            print("SQ2-45: engine %s not available: %s" % (engine, exc))
    view = want.get("view_45")
    if view and scene.view_settings.view_transform == want.get("view_36"):
        try:
            scene.view_settings.view_transform = view
        except Exception as exc:
            print("SQ2-45: view transform %s not available: %s" % (view, exc))

bpy.ops.wm.save_as_mainfile(filepath=out, check_existing=False, copy=True)
print("SQ2-45: wrote", out)
'''


def _set_enum_safe(owner, prop, value):
    try:
        setattr(owner, prop, value)
        return True
    except Exception:
        return False


def read_stamp(path):
    """Return the 5-byte version stamp of a .blend ('-v306', '-v405', ...)."""
    try:
        with open(path, "rb") as handle:
            head = handle.read(12)
    except OSError:
        return b""
    if head[:7] != b"BLENDER":
        return b""
    return head[7:12]


def _stamp_text(stamp):
    return stamp.decode("ascii", "replace") if stamp else "?"


def _stamp_number(stamp):
    """'-v405' -> 405, anything unexpected -> 0."""
    try:
        return int(stamp[2:5].decode("ascii"))
    except (TypeError, ValueError, IndexError):
        return 0


def _file_mentions(path, needle, chunk_size=4 << 20):
    """True if the saved file contains ``needle`` as a stored string.

    3.6 replaces enum values and names it does not know while loading, so the
    original text is only observable in the file bytes.
    """
    if not path:
        return False
    marker = needle.encode("ascii") + b"\0"
    try:
        with open(path, "rb") as handle:
            tail = b""
            while True:
                chunk = handle.read(chunk_size)
                if not chunk:
                    return False
                if marker in tail + chunk:
                    return True
                tail = chunk[-len(marker):]
    except OSError:
        return False


def _arch_tokens():
    """Folder-name tokens that mark a 4.x build for this machine's CPU."""
    machine = platform.machine().lower()
    if machine in ("arm64", "aarch64"):
        return ("arm64",)
    if machine in ("amd64", "x86_64", "x64"):
        return ("x64", "amd64")
    return ()


def blender45_exe():
    """Locate the Blender 4.5 binary used to write files back as 4.5."""
    global _45_EXE
    # The environment always wins, so setting it mid-session works too.
    path = os.environ.get("BLENDER45_EXE")
    if path and os.path.isfile(path):
        return path
    if _45_EXE is not False:
        return _45_EXE

    # A 4.x build unpacked next to this install: .../Blender36/ and .../blender-4.5.16/
    root = os.path.dirname(os.path.abspath(bpy.app.binary_path))
    parent = os.path.dirname(root)
    candidates = []
    try:
        for name in os.listdir(parent):
            if not name.lower().startswith("blender-4."):
                continue
            candidate = os.path.join(parent, name, "blender.exe")
            if os.path.isfile(candidate):
                candidates.append((name, candidate))
    except OSError:
        pass
    if candidates:
        # Prefer a build for this CPU. A plain sort is wrong: "...-windows-arm64"
        # sorts before "...-windows-x64", so on the SQ2 it would hand every save
        # to the emulated x64 4.5 instead of the native ARM64 one.
        tokens = _arch_tokens()
        candidates.sort(key=lambda item: (any(t in item[0].lower() for t in tokens), item[0]))
        _45_EXE = candidates[-1][1]
        return _45_EXE

    _45_EXE = None
    return None


def record_restore(scene, engine_45=None, view_45=None):
    entry = RESTORE.setdefault(scene.name, {})
    if engine_45:
        entry["engine_45"] = engine_45
        entry["engine_36"] = ENGINE_MAP.get(engine_45, entry.get("engine_36"))
    if view_45:
        entry["view_45"] = view_45
        entry["view_36"] = VIEW_TRANSFORM_MAP.get(view_45, entry.get("view_36"))


def fix_scene(scene, report, mention_next=False, mention_agx=False):
    engine = scene.render.engine
    if engine in ENGINE_MAP:
        new_engine = ENGINE_MAP[engine]
        if _set_enum_safe(scene.render, "engine", new_engine):
            record_restore(scene, engine_45=engine)
            report.append("engine %s -> %s (scene %r)" % (engine, new_engine, scene.name))
        else:
            report.append("engine %s could not be remapped (scene %r)" % (engine, scene.name))
    elif engine not in KNOWN_36_ENGINES:
        report.append("engine %s unknown to 3.6 (scene %r)" % (engine, scene.name))
    elif mention_next and engine == "BLENDER_EEVEE":
        # 3.6 already fell back on its own; the file still names EEVEE Next, so
        # remember it and let the 4.5 step put it back.
        record_restore(scene, engine_45="BLENDER_EEVEE_NEXT")
        report.append("engine EEVEE Next recorded for the 4.5 save (scene %r)" % scene.name)

    view = scene.view_settings.view_transform
    if view in VIEW_TRANSFORM_MAP:
        new_view = VIEW_TRANSFORM_MAP[view]
        if _set_enum_safe(scene.view_settings, "view_transform", new_view):
            record_restore(scene, view_45=view)
            report.append("view transform %s -> %s (scene %r)" % (view, new_view, scene.name))
        else:
            report.append("view transform %s could not be remapped (scene %r)" % (view, scene.name))
    elif mention_agx and view == "Standard":
        if _set_enum_safe(scene.view_settings, "view_transform", "Filmic"):
            record_restore(scene, view_45="AgX")
            report.append("view transform AgX -> Filmic (scene %r, recovered from file)" % scene.name)
        else:
            report.append("view transform AgX could not be replaced by Filmic (scene %r)" % scene.name)

    _fixup_denoising(scene, report)


def _fixup_denoising(scene, report):
    """Clear *Denoise* when this build has no OpenImageDenoise.

    A 4.5 scene almost always asks Cycles to denoise. The arm64 OIDN has no
    device, so OIDN is configured out of this build and a denoise request fails
    the render outright (`Build without OpenImageDenoiser`) rather than saving
    anything. Clearing the flag on load turns that hard failure into the frame
    the scene would have rendered un-denoised.
    """
    options = getattr(bpy.app, "build_options", None)
    if options is not None and getattr(options, "openimagedenoise", False):
        return
    try:
        cycles = scene.cycles
    except Exception:
        return
    if not getattr(cycles, "use_denoising", False):
        return
    try:
        cycles.use_denoising = False
    except Exception:
        report.append("denoising could not be cleared (scene %r)" % scene.name)
        return
    report.append("denoising turned off, no OpenImageDenoise in this build (scene %r)"
                  % scene.name)


def fixup_loaded_file(filepath=""):
    """Repair everything 3.6 had to substitute when the file was read.

    Files are assumed to be 4.5, so this runs on every load rather than only
    when the stamp looks newer. An empty path is the startup/default scene,
    which needs no repair and would otherwise print on every launch.
    """
    global LAST_REPORT
    path = filepath or bpy.data.filepath
    if not path:
        return []
    mention_next = _file_mentions(path, "BLENDER_EEVEE_NEXT")
    mention_agx = _file_mentions(path, "AgX")

    report = []
    for scene in bpy.data.scenes:
        fix_scene(scene, report, mention_next=mention_next, mention_agx=mention_agx)
    if not report:
        report.append("no fixups needed (materials, objects and node types mapped natively)")

    stamp = read_stamp(path)
    if stamp:
        report.insert(0, "opened %s file %s" % (_stamp_text(stamp), path))
    LAST_REPORT = report
    for line in report:
        print("%s: %s" % (BRIDGE_TAG, line))
    return report


def _under(path, directory):
    if not directory:
        return False
    path = os.path.abspath(path).lower()
    directory = os.path.abspath(directory).lower()
    return path == directory or path.startswith(directory + os.sep)


def _is_temp(path):
    return _under(path, getattr(bpy.app, "tempdir", "") or "")


def _own_file_reason(path):
    """Why ``path`` has to stay untouched, or '' when it is a normal user file."""
    if os.path.basename(path).lower() in CONFIG_NAMES:
        return "Blender's own config file"
    install = os.path.dirname(os.path.abspath(bpy.app.binary_path))
    if _under(path, install):
        return "inside the Blender install"
    try:
        config = bpy.utils.user_resource("CONFIG")
    except Exception:
        config = ""
    if _under(path, config or ""):
        return "in Blender's config directory"
    return ""


def _is_blender_own_file(path):
    """True for Blender's own config/install files, which must stay untouched."""
    return bool(_own_file_reason(path))


def should_convert(path):
    """Whether a file 3.6 just wrote has to be re-saved as 4.5."""
    if not path or not os.path.isfile(path):
        return False
    if os.environ.get("SQ2_NO_45_SAVE") == "1":
        return False
    if _is_temp(path):
        return False
    reason = _own_file_reason(path)
    if reason:
        print("%s: %s is %s, left in %s format"
              % (BRIDGE_TAG, path, reason, _stamp_text(read_stamp(path))))
        return False
    stamp = read_stamp(path)
    if not stamp:
        return False
    # Only a 3.6-format file needs converting; a 4.x one is already right.
    return _stamp_number(stamp) < 400


def convert_to_45(path, why="save"):
    """Re-save ``path`` as a 4.5 file by running Blender 4.5 on it."""
    global _CONVERTING
    if _CONVERTING:
        return False
    _CONVERTING = True
    out = path + ".45tmp.blend"
    cfg = path + ".45tmp.json"
    script = path + ".45tmp.py"
    try:
        exe = blender45_exe()
        if not exe:
            print("%s: ERROR no Blender 4.5 binary found (set BLENDER45_EXE); "
                  "%s left in %s format" % (BRIDGE_TAG, path, _stamp_text(read_stamp(path))))
            return False

        with open(cfg, "w", encoding="utf-8") as handle:
            json.dump({"restore": RESTORE}, handle)
        with open(script, "w", encoding="utf-8") as handle:
            handle.write(FOUR5_SCRIPT)

        command = [
            exe, "-b", path, "--factory-startup", "--python-exit-code", "1",
            "--python", script, "--", out, cfg,
        ]
        try:
            proc = subprocess.run(command, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, timeout=600)
        except (OSError, subprocess.SubprocessError) as exc:
            print("%s: ERROR Blender 4.5 could not run (%s); %s left in %s format"
                  % (BRIDGE_TAG, exc, path, _stamp_text(read_stamp(path))))
            return False

        output = proc.stdout.decode("utf-8", "replace") if proc.stdout else ""
        stamp = read_stamp(out)
        if proc.returncode != 0 or _stamp_number(stamp) < 400:
            print("%s: ERROR Blender 4.5 did not write a 4.x file (exit %s, stamp %s); "
                  "%s left in %s format" % (BRIDGE_TAG, proc.returncode, _stamp_text(stamp),
                                            path, _stamp_text(read_stamp(path))))
            for line in output.strip().splitlines()[-20:]:
                print("%s: 4.5| %s" % (BRIDGE_TAG, line))
            return False

        for attempt in range(4):
            try:
                os.replace(out, path)
                break
            except OSError:
                if attempt == 3:
                    print("%s: ERROR could not replace %s (locked); the 4.5 file is at %s"
                          % (BRIDGE_TAG, path, out))
                    return False
                time.sleep(0.25)

        print("%s: %s written as Blender %s (%s)"
              % (BRIDGE_TAG, path, _stamp_text(stamp), why))
        return True
    finally:
        _CONVERTING = False
        for leftover in (out, out + "1", cfg, script):
            try:
                os.remove(leftover)
            except OSError:
                pass


@persistent
def _load_post(filepath=""):
    fixup_loaded_file(filepath)


@persistent
def _save_post(filepath=""):
    """Every save of a user file is handed to Blender 4.5 straight away."""
    save_as_45(getattr(bpy.data, "filepath", "") or filepath)


def save_as_45(path):
    if not should_convert(path):
        return False
    return convert_to_45(path, why="save")


@persistent
def _depsgraph_update(*_args):
    """Catch engines from data appended/linked out of a 4.5 library.

    3.6 has no append/link handler, so this runs on dependency-graph updates
    and only touches scenes whose engine actually changed.
    """
    for scene in bpy.data.scenes:
        engine = scene.render.engine
        if _SEEN_ENGINE.get(scene.name) == engine:
            continue
        _SEEN_ENGINE[scene.name] = engine
        if engine in ENGINE_MAP:
            mapped = ENGINE_MAP[engine]
            if _set_enum_safe(scene.render, "engine", mapped):
                record_restore(scene, engine_45=engine)
                _SEEN_ENGINE[scene.name] = mapped
                print("%s: appended data used %s -> %s (scene %r)"
                      % (BRIDGE_TAG, engine, mapped, scene.name))


def register():
    # scripts/startup modules can be imported more than once per session, and a
    # second import creates fresh function objects; keep a single registration.
    import builtins

    if getattr(builtins, "_sq2_bridge_registered", False):
        return
    builtins._sq2_bridge_registered = True
    if _load_post not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(_load_post)
    if _save_post not in bpy.app.handlers.save_post:
        bpy.app.handlers.save_post.append(_save_post)
    if _depsgraph_update not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(_depsgraph_update)
    exe = blender45_exe()
    print("%s: active (this build %s, saves as 4.5 via %s)"
          % (BRIDGE_TAG, ".".join(str(x) for x in CURRENT), exe or "MISSING - set BLENDER45_EXE"))


def unregister():
    for handler, collection in (
        (_load_post, bpy.app.handlers.load_post),
        (_save_post, bpy.app.handlers.save_post),
        (_depsgraph_update, bpy.app.handlers.depsgraph_update_post),
    ):
        if handler in collection:
            collection.remove(handler)


register()
