# Blender 3.6 on the SQ2: 4.5 → 3.6 conversion, and the ARM64 build question

Two separate things were asked for: an **ARM64 build of Blender 3.6**, and a
**bridge that uses the ARM64 Blender 4.5 build to convert newer files** into
something 3.6 can open. The bridge is implemented and measured. The ARM64
build of 3.6 is a porting project, blocked on missing dependencies — details
in the last section; the assistant did **not** produce an ARM64 3.6 binary.

Measured with:
- Blender 4.5.16 LTS, ARM64 native (`blender-4.5.16-windows-arm64/`)
- Blender 3.6.23 x64 official (`blender-3.6.23-windows-x64/`), running under
  Windows x64 emulation on the SQ2
- source tree `blender-blender-v3.6-release/` (v3.6.23, release cycle)

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

## 2. The bridge (implemented, tested)

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

Verified end to end (`work/bridge_save3.log`, `work/reopen36b.log`):

```
SQ2-BRIDGE: file version 4.5.92 is newer than this build 3.6.23
SQ2-BRIDGE: view transform AgX -> Filmic (scene 'Scene', recovered from file)
SQ2-BRIDGE: wrote .../work/test45.v36.blend (2 report lines)
```

and the written file is stamped `-v306`, reopens in 3.6 with
`SCENE_ENGINE BLENDER_EEVEE`, `VIEW_TRANSFORM Filmic`, all five Principled
values and the geometry-nodes modifier intact, and no "newer binary" warning.

## 3. Why there is no ARM64 3.6 build yet

Everything below was checked in this tree; the numbers are what the checks
returned, not estimates.

1. **No ARM64 dependencies exist for 3.6.** `blender-blender-v3.6-release/
   .gitmodules` declares exactly four lib submodules — `lib/linux_x64`,
   `lib/macos_arm64`, `lib/macos_x64`, `lib/windows_x64` — all with
   `update = none` and all empty here. There is no `lib/windows_arm64` branch
   in the v3.6 lib set at all: Blender's Windows-on-ARM dependency set and the
   `lib-windows_arm64` repo were created for 4.2 (Linaro, merged March 2024),
   which is why the 5.2 workflow in this repo can do
   `git submodule update --init lib/windows_arm64` and 3.6 cannot.
2. **3.6's build system has no Windows ARM64 support.**
   `grep -rn "arm64\|aarch64" build_files/cmake/platform/platform_win32.cmake
   platform_win32_msvc.cmake` returns nothing; the only `arm64` in
   `CMakeLists.txt` is the macOS `CMAKE_OSX_ARCHITECTURES` branch.
3. **Python 3.10 is pinned.** `FindPythonLibsUnix.cmake` has
   `_PYTHON_VERSION_SUPPORTED 3.10`. ARM64 CPython 3.10 exists only as the
   nuget `pythonarm64` build (3.10.11), not as part of any Blender lib set,
   and 3.6 links `python310.lib` by name.
4. **The toolchain is not the problem.** A native ARM64 MSVC is installed:
   `C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Tools\
   MSVC\14.51.36231\{Hostarm64,Hostx64}`, with CMake and Ninja under
   `...\Common7\IDE\CommonExtensions\Microsoft\CMake\`. The source is not
   hostile to ARM64 either — `BLI_simd.h` already supports SSE2-on-NEON via
   `WITH_SSE2NEON` (used for Apple Silicon), and Cycles has an
   `__aarch64__`/`_M_ARM64` path. The gap is dependencies plus the Windows
   build-system branch.

### What a port would take

1. Backport 4.2's Windows-ARM64 build support: `lib/windows_arm64` in
   `build_files/cmake/platform/platform_win32.cmake` (arch detection, `arm64`
   generator/`-A ARM64`, lib path, `WITH_SSE2NEON` for MSVC), plus the
   `make.bat`/`build_files/utils` pieces.
2. Assemble a dependency set for arm64 at 3.6-era versions (zlib, OpenEXR,
   Imath, OpenImageIO, TBB, Boost, Alembic, USD, OpenSubdiv, OIDN, FFmpeg,
   FreeType, SDL, GLEW, epoxy, Python 3.10 + numpy). Two routes: build them
   with `build_files/build_environment` (which has `linux/` and `windows/`
   folders but no arm64 configuration) or start from 4.2–4.5's
   `lib/windows_arm64` and back-port 3.6's code to the newer APIs (Python
   3.11 instead of 3.10, OIIO 3.2, USD 24.x).
3. Iterate the build. Expect a first wave of errors in GHOST's Win32 layer,
   `intern/atomic`, OIIO/USD call sites, and the Python bindings.

Realistic effort: several CI rounds on `windows-11-arm` (the runner this repo
already uses) and a multi-day timebox, with no guarantee of a fully working
build. Nothing in that list is blocked on the user, but it is much larger than
"build it".

### Working alternative available today

The official 3.6.23 x64 build runs on this machine under x64 emulation — it
produced every result in section 1 — and with the bridge it opens 4.5 files
and saves genuine 3.6 files. So 3.6 scenes can be worked on now; only the
"native ARM64" property is missing until the port above is done.

## 4. Not verified

- No ARM64 3.6 binary exists, so nothing about ARM64-native 3.6 behaviour is
  measured.
- The conversion table covers one synthetic scene: materials with Principled
  v2, emission, one geometry-nodes modifier, one light, one camera. Libraries,
  linked assets, drivers, simulation caches, EEVEE Next-specific settings
  (shadow/render properties added in 4.2+) and video sequencer data were not
  tested.
- Rendering quality after the AgX→Filmic change was not compared.

## 5. Port plan: lite first, full is additive

Decision: build a **lite** ARM64 3.6 first (`WITH_CYCLES/USD/ALEMBIC/OIDN/FFMPEG/
OPENVDB/OPENSUBDIV` off), then add modules. This is a prefix, not a detour: the
whole Windows-ARM64 delta in Blender's build system is four hunks in one file,
shared by both builds.

`custom-driver/blender36/0001-windows-arm64-build-support.patch` (against
`build_files/cmake/platform/platform_win32.cmake`, verified to apply as 4
hunks):

1. `/Zc:preprocessor` for both C and C++ when `CMAKE_SYSTEM_PROCESSOR` is
   `ARM64` — sse2neon does not compile without it (same as upstream 4.2).
2. `/MACHINE:ARM64` instead of `/MACHINE:X64`.
3. `LIBDIR_BASE windows_arm64` instead of `windows_x64`.
4. Boost suffix `vc143-mt-a64-<ver>` instead of `vc142-mt-x64-<ver>`.

Full (Cycles, USD, Alembic, OIDN, FFmpeg) differs only by CMake options and by
extra dependency directories; the four hunks above are unchanged, plus
`WITH_SSE2NEON` already handled by `BLI_simd.h`.

### Dependency routes

- **A (chosen for lite): 4.2 arm64 lib set + injected Python 3.10.**
  `lib-windows_arm64` exists only from `blender-v4.2-release` on. 3.6 expects
  `${LIBDIR}/python/310/{bin,include,libs,lib/site-packages}`, and 3.6 pins
  Python 3.10, so ARM64 CPython 3.10.11 (nuget `pythonarm64`, laid out as
  `python/310/`) is injected into `lib/windows_arm64/`. Keeps 3.6's Python code
  untouched; the risk moves to newer OIIO/OpenEXR/TBB headers.
- **B (only if A's API drift is too wide): build 3.6-vintage deps for arm64.**
  Port `build_files/build_environment` (has `linux/` and `windows/`, no arm64
  configuration). More dep work, less 3.6 code churn.

### Still to do

1. CI workflow on `windows-11-arm`: clone v3.6.23, add `lib/windows_arm64`
   (4.2 branch), overlay `python/310`, apply the patch, configure with the
   `Visual Studio 17 2022` generator + `-A ARM64`, build, upload artifact.
2. Iterate on the first real compile error per round (expected: GHOST Win32,
   `intern/atomic`, OIIO/USD call sites, Python bindings).
3. Add modules back (Cycles first) once lite links.
