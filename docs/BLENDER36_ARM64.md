# Blender 3.6 on the SQ2: 4.5 → 3.6 conversion, and the ARM64 build

Two separate things were asked for: an **ARM64 build of Blender 3.6**, and a
**bridge that uses the ARM64 Blender 4.5 build to convert newer files** into
something 3.6 can open.

Both now exist and are measured. The ARM64 3.6 build is a *lite* build (no
Cycles/USD/Alembic/OIDN/FFmpeg/OpenVDB/OpenSubdiv/Collada) and the bridge was
re-run end to end on it: a 4.5 scene opened natively, was repaired, and was
written as a genuine 3.6 file. Sections 1–2 are the conversion behaviour, 3 is
the build, 4 lists what is still unverified.

Measured with:
- Blender 4.5.16 LTS, ARM64 native (`blender-4.5.16-windows-arm64/`)
- Blender 3.6.23 **ARM64 native**, built by CI (artifact `blender36-lite-arm64`,
  unpacked as `artifacts/r19/`)
- Blender 3.6.23 x64 official (`blender-3.6.23-windows-x64/`), under Windows
  x64 emulation on the SQ2, for comparison
- source tree `blender-blender-v3.6-release/` (v3.6.23)

## 1. What actually happens when 3.6.23 opens a 4.5 file

Nothing is refused. 3.6 prints `File written by newer Blender binary (405.92),
expect loss of data!` and then loads, because Blender reads data by struct and
field name (SDNA) and runs its own versioning migration for older/newer files.

A 4.5 scene (cube with a Principled v2 material, a sun, a camera, a Set
Position geometry-nodes modifier, `BLENDER_EEVEE_NEXT`, AgX) opened in 3.6.23:

| data | result in 3.6 |
| --- | --- |
| objects, camera, mesh | intact |
| `Base Color`, `Metallic`, `Roughness`, `IOR` | intact |
| `Transmission Weight` → `Transmission` | **intact (0.6)** |
| `Subsurface Weight` → `Subsurface` | **intact (0.2)** |
| `Specular IOR Level` → `Specular` | **intact (0.7)** |
| `Sheen Weight` → `Sheen` | **intact (0.5)** |
| `Coat Weight` → `Clearcoat` | **intact (0.8)** |
| `Emission Color` / `Emission Strength` | **intact (0.1, 0.9, 0.2 / 0.9)** |
| geometry-nodes modifier | intact, `GeometryNodeSetPosition` preserved |
| `BLENDER_EEVEE_NEXT` engine | **lost** — error, silently becomes `BLENDER_EEVEE` |
| AgX view transform | **lost** — silently becomes `Standard` |
| UI regions (types 14/15) | removed with warnings, harmless |

Two consequences worth recording:

1. **Do not rewrite the version stamp.** A copy of the 4.5 file with the header
   changed from `-v405` to `-v306` loads with *less* data: `Transmission` and
   `Subsurface` came back as `0.0`, because the version-tagged migration is
   skipped when the file claims to be a 3.6 file. The stamp tells the truth and
   must stay that way; `tools/blender36/blend_stamp.py` exists to read it, and
   its `set` mode is a diagnostic, not part of the conversion path.
2. The two real losses (engine, view transform) happen *inside* the load, so
   they have to be repaired after loading — that is what the bridge does.

## 2. The bridge

| file | what it is |
| --- | --- |
| `tools/blender36/bridge/sq2_legacy_bridge.py` | 3.6 startup module: fixes engine + view transform on load, adds `File > Save 3.6 Copy` (`wm.save_36_copy`), reports what happened |
| `tools/blender36/install_bridge.py` | copies the module into `<3.6 install>/3.6/scripts/startup/` |
| `tools/blender36/blender36.cmd` | launcher: finds the 3.6 install, keeps the bridge in sync, runs it with your arguments |
| `tools/blender36/blend_stamp.py` | reads/rewrites the `-vXXX` header stamp (diagnostic) |
| `tools/blender36/make_test_scene.py` | builds the 4.5 probe scene used for the table above |
| `tools/blender36/inspect_blend.py` | dumps objects/materials/nodes/engine/view transform of a file |

Behaviour:

- `BLENDER_EEVEE_NEXT` → `BLENDER_EEVEE`. Note 3.6 falls back on its own at
  load time, so the `Engine 'BLENDER_EEVEE_NEXT' not available` error line is
  expected and unavoidable without patching 3.6's reader.
- AgX → Filmic. 3.6 has already reset the unknown transform to `Standard` by
  the time the handler runs, so the bridge checks the file bytes for the
  string `AgX` (`_file_mentions_agx`) and only then switches to Filmic.
- `SQ2_AUTO_SAVE=1` writes `<name>.v36.blend` next to the opened file; the
  `wm.save_36_copy` operator does the same on demand.
- Every run prints `SQ2-BRIDGE:` lines, so the conversion is visible in logs
  instead of happening silently.

### Verified on the native ARM64 build

`work/test45.blend` (4.5.92) copied to `work/test45_arm64.blend`, opened with
the ARM64 3.6 and `SQ2_AUTO_SAVE=1`:

```
SQ2-BRIDGE: active (this build 3.6.23)
SQ2-BRIDGE: file version 4.5.92 is newer than this build 3.6.23
SQ2-BRIDGE: view transform AgX -> Filmic (scene 'Scene', recovered from file)
SQ2-BRIDGE: no fixups needed (materials, objects and node types mapped natively)
SQ2-BRIDGE: wrote .../work/test45_arm64.v36.blend (2 report lines)
```

`tools/blender36/inspect_blend.py` on the written file, in the same ARM64
build, reports `SCENE_ENGINE BLENDER_EEVEE`, `VIEW_TRANSFORM Filmic`, all five
Principled values (Transmission 0.6, Subsurface 0.2, Specular 0.7, Sheen 0.5,
Clearcoat 0.8, IOR 1.45), the emission colour/strength, and the `Sq2GN`
geometry-nodes modifier with its `GeometryNodeSetPosition` node intact. That is
the same result the x64 build produced, now with no x64 emulation involved.

## 3. The ARM64 3.6 build

`.github/workflows/blender36-arm64.yml` builds it on the `windows-11-arm`
runner, and `.github/workflows` run **44186006385** (round 19) completed every
step: source clone, 4.2 `lib-windows_arm64` fetch, ARM64 CPython 3.10.11
injection, patch application, configure, `[4757/4757]` build, link, PE check
(`0xAA64`), `cmake --install`, runtime staging, and an artifact upload.

The artifact (`blender36-lite-arm64`, 267 MB unpacked) was downloaded to
`artifacts/r19/` and run on this machine:

```
Blender 3.6.23
	build date: 2026-11-17
	build time: 22:32:51
	build hash: e467db79ca8c
	build platform: Windows
	build link flags: /MACHINE:ARM64 ...
```

`blender.exe --version` exits 0, and the import scan (`work/scan_deps.py`)
resolves every non-`api-ms-win-*`/`ext-ms-*` dependency out of the tree.

### What it took

Two ingredients were missing rather than one: 3.6 has no Windows-ARM64 branch
in its build system and no ARM64 dependency set (the `lib-windows_arm64` repo
and Blender's Windows-on-ARM support were created for 4.2), and its Python
pin is 3.10, which only exists for ARM64 as the nuget `pythonarm64` build. The
route taken is the 4.2 arm64 dependency set plus an injected CPython 3.10.11.

`custom-driver/blender36/` holds the eleven patches; each one is the smallest
change that fixes a real compile/install error and, where upstream 4.2 already
solved the same problem, is modelled on it:

| patch | what it fixes |
| --- | --- |
| `0001` | Windows-ARM64 build support in `platform_win32.cmake`: `/Zc:preprocessor`, `/MACHINE:ARM64`, `LIBDIR_BASE windows_arm64`, `vc143-mt-a64` Boost suffix |
| `0002` | GHOST Wintab `PRINTF` varargs with the conforming preprocessor |
| `0003` | LZO `_M_ARM64` arch test |
| `0004` | `RNA_warning(format, ...)` format-only calls (needs `_MSVC_TRADITIONAL` split) |
| `0005` | `BLI_cpu_brand_string()` / SSE4.1 detection call x86-only `__cpuid` |
| `0006` | ARM64 stack walk (`Pc`/`Fp`/`Sp`, `IMAGE_FILE_MACHINE_ARM64`) |
| `0007` | `CD_FAKE_*` layer ids OR-ed into an enum (C5287 under `/WX`) |
| `0008` | `BM_ALL` mask cast to `int` |
| `0009` | ARM64 OIIO needs the separate `imath` include dir (same hunk as 4.2) |
| `0010` | 4.2 ships FFTW static, so `libfftw3-3.dll` never exists |
| `0011` | 4.2 names gmp `gmp-10.dll`, not `libgmp-10.dll` |

Staging is `custom-driver/blender36/stage_runtime.py`: it walks `blender.exe`'s
import graph transitively, copies anything missing out of
`lib/windows_arm64`, skips `api-ms-win-*`/`ext-ms-*` (operating system), and
exits non-zero if a real DLL is unresolved — which is what kept
`avcodec-60.dll`'s `swresample-4.dll` and OIIO's
`boost_thread-vc143-mt-a64-1_82.dll` from being silently dropped.

Round-by-round history, with the exact error text of each failure, is in
`docs/BLENDER36_ARM64_ITERATIONS.md`.

### Using it

1. Download the `blender36-lite-arm64` artifact from the workflow run and
   unpack it somewhere permanent, e.g. `C:\Blender36ARM64`.
2. `python tools/blender36/install_bridge.py C:\Blender36ARM64`
3. `set BLENDER36_HOME=C:\Blender36ARM64` and launch through
   `tools\blender36\blender36.cmd scene.blend`, or open files directly in
   `blender.exe` (the bridge is loaded from `3.6/scripts/startup` either way).

### What the lite set leaves out

`WITH_CYCLES/USD/ALEMBIC/OPENIMAGEDENOISE/FFMPEG/OPENVDB/OPENSUBDIV/COLLADA/
OPENCOLLADA/POTRACE/BOOST/HYDRA/XR_OPENXR=OFF`. Cycles renders, USD/Alembic
import-export, FFmpeg video output, OpenVDB volumes, OpenSubdiv, Collada and
the Hydra/MaterialX viewport integrations are therefore absent; EEVEE,
Workbench, modelling, materials, geometry nodes and Python scripting are
present. Adding them back is a CMake-option change plus whatever dependency
version drift shows up — the ARM64 build-system delta itself is already in.

## 4. Not verified

- The GUI was not driven on the SQ2: the build was exercised in background mode
  (`--version`, `--python`, file open/save). Viewport behaviour on the Adreno
  GPU is untested for this build.
- The lite set means nothing Cycles/USD/FFmpeg/OpenVDB-related is measured.
- **numpy is not in the tree.** The injected CPython 3.10.11 has no numpy
  binary for win_arm64 (no wheel exists), so only numpy's C headers are
  present, which is enough to compile the `aud` module but not to `import
  numpy` at runtime. Scripts that need numpy will fail; this is independent of
  the 4.5 → 3.6 conversion.
- The conversion table covers one synthetic scene: materials with Principled
  v2, emission, one geometry-nodes modifier, one light, one camera. Libraries,
  linked assets, drivers, simulation caches, EEVEE Next-specific settings
  (shadow/render properties added in 4.2+) and video sequencer data were not
  tested.
- Rendering quality after the AgX→Filmic change was not compared.

## 5. History of the port

Kept because the constraints are easy to re-hit: 3.6's `.gitmodules` has no
`lib/windows_arm64` (only linux_x64, macos_arm64, macos_x64, windows_x64, all
`update = none`), `platform_win32.cmake` had no `arm64`/`aarch64` mention,
`FindPythonLibsUnix.cmake` pins `_PYTHON_VERSION_SUPPORTED 3.10`, and
`make.bat`'s Visual Studio generator cannot find the arm64 runner's VS
2026 — hence Ninja plus `vcvarsall arm64`.

Two further packaging facts, found only after the build linked, are worth
recording because they make a *working* install differ from a *linking* one:

- `scripts/addons` is not in the 3.6 source repo. The release process clones
  `blender-addons` into it (`make_update.py`, `external_scripts_update`), so a
  plain clone builds a Blender that cannot enable a single add-on, FBX/OBJ/glTF
  included. The workflow now clones `blender-addons` at `v3.6.23` and the
  smoke test imports `io_scene_fbx`.
- `WITH_PYTHON_INSTALL=OFF` (the first lite configuration) produces a tree with
  no `3.6/python` at all: the exe starts, prints `--version`, and then dies on
  `ModuleNotFoundError: No module named 'encodings'` as soon as Python
  initialises — which is to say, for the bridge, immediately. The workflow now
  installs Python and checks that `encodings` and `bpy` import.
