"""SQ2 legacy bridge — auto-fixup of newer .blend files inside Blender 3.6.

Install into a Blender 3.6 install as ``3.6/scripts/startup/sq2_legacy_bridge.py``
(see tools/blender36/install_bridge.py). Modules under ``scripts/startup`` are
imported at boot, so the handlers below are active without enabling an add-on.

What it fixes, based on measured behaviour of 3.6.23 opening 4.5 files
(docs/BLENDER36_ARM64.md):

* ``BLENDER_EEVEE_NEXT`` -> ``BLENDER_EEVEE`` (3.6 has no EEVEE Next; the
  engine name silently falls back otherwise).
* AgX view transform -> Filmic (3.6 has no AgX; falls back to Standard, which
  looks wrong).
* Reports scene data that 3.6 cannot represent, so nothing is lost silently.

Data that needs no fixing: Principled v2 sockets are mapped by Blender's own
versioning (Transmission Weight -> Transmission, Coat Weight -> Clearcoat,
Sheen Weight -> Sheen, Specular IOR Level -> Specular, emission colour and
strength), and node types shared with 3.6 survive as-is.
"""
import os

import bpy
from bpy.app.handlers import persistent

BRIDGE_TAG = "SQ2-BRIDGE"

# Version at which this build stops being able to read files natively.
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

LAST_REPORT = []


def _file_is_newer():
    try:
        return tuple(bpy.data.version) > CURRENT
    except Exception:
        return False


def _set_enum_safe(owner, prop, value):
    try:
        setattr(owner, prop, value)
        return True
    except Exception:
        return False


def _file_mentions_agx(path):
    """True if the saved file names the AgX transform.

    3.6 resets an unknown view transform to Standard while loading, so the
    original name is gone by load_post; the only way to know is the file
    itself, where the name is stored as a null-terminated string.
    """
    try:
        with open(path, "rb") as fh:
            tail = b""
            while True:
                chunk = fh.read(4 << 20)
                if not chunk:
                    return False
                if b"AgX\x00" in tail + chunk:
                    return True
                tail = chunk[-4:]
    except OSError:
        return False


def fix_scene(scene, report, used_agx=False):
    engine = scene.render.engine
    if engine in ENGINE_MAP:
        new_engine = ENGINE_MAP[engine]
        if _set_enum_safe(scene.render, "engine", new_engine):
            report.append("engine %s -> %s (scene %r)" % (engine, new_engine, scene.name))
        else:
            report.append("engine %s could not be remapped (scene %r)" % (engine, scene.name))
    elif engine not in KNOWN_36_ENGINES:
        report.append("engine %s unknown to 3.6 (scene %r)" % (engine, scene.name))

    view = scene.view_settings.view_transform
    if view in VIEW_TRANSFORM_MAP:
        new_view = VIEW_TRANSFORM_MAP[view]
        if _set_enum_safe(scene.view_settings, "view_transform", new_view):
            report.append("view transform %s -> %s (scene %r)" % (view, new_view, scene.name))
        else:
            report.append("view transform %s could not be remapped (scene %r)" % (view, scene.name))
    elif used_agx and view == "Standard":
        # 3.6 already reset the missing AgX transform to Standard on load.
        if _set_enum_safe(scene.view_settings, "view_transform", "Filmic"):
            report.append("view transform AgX -> Filmic (scene %r, recovered from file)" % scene.name)
        else:
            report.append("view transform AgX could not be replaced by Filmic (scene %r)" % scene.name)


def collect_data_loss(report, used_agx=False):
    """Things 3.6 cannot represent, listed so the conversion is not silent."""
    for scene in bpy.data.scenes:
        fix_scene(scene, report, used_agx=used_agx)


def fixup_if_newer():
    global LAST_REPORT
    if not _file_is_newer():
        return []
    report = ["file version %s is newer than this build %s"
              % (".".join(str(x) for x in bpy.data.version), ".".join(str(x) for x in CURRENT))]
    fixes = []
    collect_data_loss(fixes, used_agx=_file_mentions_agx(bpy.data.filepath))
    if not fixes:
        fixes.append("no fixups needed (materials, objects and node types mapped natively)")
    report.extend(fixes)
    LAST_REPORT = report
    for line in report:
        print("%s: %s" % (BRIDGE_TAG, line))
    return report


@persistent
def _load_post(*_args):
    report = fixup_if_newer()
    if report and os.environ.get("SQ2_AUTO_SAVE") == "1":
        path = bpy.data.filepath
        if path:
            auto = os.path.splitext(path)[0] + ".v36.blend"
            bpy.ops.wm.save_36_copy(filepath=auto)


class WM_OT_save_36_copy(bpy.types.Operator):
    """Save this scene as a 3.6 file, after applying bridge fixups"""

    bl_idname = "wm.save_36_copy"
    bl_label = "Save 3.6 Copy"
    bl_options = {"REGISTER"}

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    check_existing: bpy.props.BoolProperty(default=False)

    def invoke(self, context, event):
        if not self.filepath:
            self.filepath = os.path.splitext(bpy.data.filepath)[0] + ".v36.blend"
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        report = fixup_if_newer()
        path = bpy.path.abspath(self.filepath)
        bpy.ops.wm.save_as_mainfile(filepath=path, check_existing=self.check_existing, copy=True)
        print("%s: wrote %s (%d report lines)" % (BRIDGE_TAG, path, len(report)))
        self.report({"INFO"}, "Saved 3.6 copy: %s" % path)
        return {"FINISHED"}


def register():
    # scripts/startup modules can be imported more than once per session, and a
    # second import creates fresh function objects; keep a single registration.
    import builtins

    if getattr(builtins, "_sq2_bridge_registered", False):
        return
    builtins._sq2_bridge_registered = True
    if not hasattr(bpy.types, WM_OT_save_36_copy.__name__):
        bpy.utils.register_class(WM_OT_save_36_copy)
    if _load_post not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(_load_post)
    print("%s: active (this build %s)" % (BRIDGE_TAG, ".".join(str(x) for x in CURRENT)))


def unregister():
    bpy.utils.unregister_class(WM_OT_save_36_copy)
    if _load_post in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_load_post)


register()
