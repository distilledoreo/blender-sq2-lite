# Blender 3.6 on the SQ2: 4.5 → 3.6 conversion, and the ARM64 build

Two separate things were asked for: an **ARM64 build of Blender 3.6**, and a
**bridge that uses the ARM64 Blender 4.5 build to convert newer files** into
something 3.6 can open.

Both now exist and are measured. The build originally shipped as a *lite* set
(EEVEE/Workbench only); it now builds the full feature set — Cycles, USD,
Alembic, OpenVDB, OpenSubdiv, OpenImageDenoise, Collada, Potrace, Boost, OpenXR
and FFmpeg — with two exceptions recorded in section 3. The bridge was re-run
end to end on the lite artifact: a 4.5 scene opened natively, was repaired, and
was written as a genuine 3.6 file. Sections 1–2 are the conversion behaviour, 3
is the build, 4 lists what is still unverified.

Measured with:
- Blender 4.5.16 LTS, ARM64 native (`blender-4.5.16-windows-arm64/`)
- Blender 3.6.23 **ARM64 native**, built by CI (artifact `blender36-lite-arm64`
  from run 44192487368, unpacked as `artifacts/r20/`)
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

`work/test45.blend` (4.5.92) copied to `work/test45_r20.blend`, opened with the
ARM64 3.6 from round 20 and `SQ2_AUTO_SAVE=1`:

```
SQ2-BRIDGE: active (this build 3.6.23)
SQ2-BRIDGE: file version 4.5.92 is newer than this build 3.6.23
SQ2-BRIDGE: view transform AgX -> Filmic (scene 'Scene', recovered from file)
SQ2-BRIDGE: no fixups needed (materials, objects and node types mapped natively)
SQ2-BRIDGE: wrote .../work/test45_r20.v36.blend (2 report lines)
```

`tools/blender36/inspect_blend.py` on the written file, in the same ARM64
build, reports `SCENE_ENGINE BLENDER_EEVEE`, `VIEW_TRANSFORM Filmic`, all five
Principled values (Transmission 0.6, Subsurface 0.2, Specular 0.7, Sheen 0.5,
Clearcoat 0.8, IOR 1.45), the emission colour/strength, and the `Sq2GN`
geometry-nodes modifier with its `GeometryNodeSetPosition` node intact. That is
the same result the x64 build produced, now with no x64 emulation involved.

## 3. The ARM64 3.6 build

`.github/workflows/blender36-arm64.yml` builds it on the `windows-11-arm`
runner. Run **44186006385** (round 19) got through every build step — source
clone, 4.2 `lib-windows_arm64` fetch, ARM64 CPython 3.10.11 injection, patch
application, configure, `[4757/4757]` build, link, PE check (`0xAA64`),
`cmake --install`, runtime staging — but its tree had no bundled Python and no
`scripts/addons`. Run **44192487368** (round 20) fixed the packaging and
uploaded the artifact now in use: `blender36-lite-arm64`, 335 MB unpacked,
with `3.6/python/{bin,DLLs,lib}` and 104 add-ons.

That artifact was downloaded to `artifacts/r20/` and run on this machine:

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

`custom-driver/blender36/` holds the twenty-seven patches; each one is the
smallest change that fixes a real compile/install error and, where upstream 4.2
already solved the same problem, is modelled on it:

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
| `0012` | 4.2 names sndfile `sndfile.dll`, not `libsndfile-1.dll` — the missing-file `install(FILES ...)` aborted `cmake --install`, skipping `datafiles/icons` and `datafiles/studiolights` |
| `0013` | Windows-ARM64 sse2neon discovery: 3.6 wired it only into `platform_apple.cmake`/`platform_unix.cmake`, so Cycles' Neon-emulated SSE kernels had no include path on Windows (same block as 4.2) |
| `0014` | Compile the SSE kernels on MSVC ARM64: MSVC defines `_M_ARM64`, never `__ARM_NEON`, and `simd.h` included `<intrin.h>` before the Neon branch. Cycles also needs `system_cpu_support_sse41()` true, because OpenImageDenoise and the Denoise node are gated on it (same three call sites as 4.2) |
| `0015` | 4.2 ships **OpenImageDenoise 2.3**, which has no `common.lib`/`dnnl.lib` beside `OpenImageDenoise.lib`; 3.6 linked all three unconditionally |
| `0016` | The boost 3.3/3.4-era fallback rewrites the suffix to `vc142-mt-gd-x64` with a `lib` prefix — names that do not exist on ARM64, so it is skipped there |
| `0017` | Cycles' Neon `vqtbl2q_s8` wrappers pass compound literals through macro layers, which MSVC C++ rejects; the tuple objects are named instead (`math.h`, `math_float3.h`, `math_intersect.h`, `simd.h`) |
| `0018` | `profiling.cpp` includes `<chrono>` explicitly instead of relying on a transitive include |
| `0019` | Cycles' CPU brand probe uses `__cpuid`, which does not exist on ARM64 even though MSVC defines `WIN32` |
| `0020` | `_M_ARM64` joins `__KERNEL_64_BIT__` so `ccl_try_align(16)` keeps its padding, and the FPCR helpers get an MSVC branch (no inline assembly) |
| `0021` | OpenVDB 11's nanovdb conversion API is only declared with `NANOVDB_USE_OPENVDB` defined |
| `0022` | nanovdb 32.6 renamed `openToNanoVDB<GridType>(...)` to `createNanoGrid<GridType, DstBuildT>()`, which is what 4.2 calls |
| `0023` | USD 24.05's token macros do not expand under MSVC 14.5x's conforming preprocessor, so `bf_usd` builds with `/Zc:preprocessor-` |
| `0024` | The arm64 boost set is dynamic but has no `boost_python310`, so the `BOOST_ALL_DYN_LINK` detection is keyed on `boost_locale` and the Python library trigger gets its own variable |
| `0025` | `bf_usd` opts out of USD's Python support (`PXR_PYTHON_SUPPORT_ENABLED`), because the prebuilt USD would otherwise need the Python 3.11 `boost_python` this tree cannot link |
| `0026` | `usd_common.cc`'s plugin-path block (only compiled without USD Python support) uses `SEP_STR` without including `BLI_path_util.h`, which its test twin does include |
| `0027` | The arm64 OpenCOLLADA build folds PCRE into its own static libraries and ships no `pcre.lib`, which `bf_collada` links unconditionally, so `PCRE_LIBRARIES` stays unset on ARM64 |

Staging is `custom-driver/blender36/stage_runtime.py`: it walks `blender.exe`'s
import graph transitively, copies anything missing out of
`lib/windows_arm64`, skips `api-ms-win-*`/`ext-ms-*` (operating system), and
exits non-zero if a real DLL is unresolved — which is what kept
`avcodec-60.dll`'s `swresample-4.dll` and OIIO's
`boost_thread-vc143-mt-a64-1_82.dll` from being silently dropped.

Round-by-round history, with the exact error text of each failure, is in
`docs/BLENDER36_ARM64_ITERATIONS.md`.

### Using it

1. Download the `blender36-full-arm64` artifact from the workflow run and
   unpack it somewhere permanent, e.g. `C:\Blender36ARM64`.
2. `python tools/blender36/install_bridge.py C:\Blender36ARM64`
3. `set BLENDER36_HOME=C:\Blender36ARM64` and launch through
   `tools\blender36\blender36.cmd scene.blend`, or open files directly in
   `blender.exe` (the bridge is loaded from `3.6/scripts/startup` either way).

The round-20 artifact is missing `3.6/datafiles/icons` and
`3.6/datafiles/studiolights`: `cmake --install` aborted at the sndfile DLL and
never reached those rules. Without `icons` the left toolbar's tool buttons
draw as empty squares — they are `ICON_TYPE_VECTOR` icons read from
`datafiles/icons/<name>.dat` at draw time, unlike the 16 px textures in the
headers, which come from the embedded atlas. Either take the next workflow
artifact, or repair an existing tree with:

```
xcopy /s /y blender-blender-v3.6-release\release\datafiles\icons C:\Blender36ARM64\3.6\datafiles\icons\
xcopy /s /y blender-blender-v3.6-release\release\datafiles\studiolights C:\Blender36ARM64\3.6\datafiles\studiolights\
```

### Feature sets

`ci_configure_arm64.bat <src> [full|lite]` takes the set, and the workflow's
`features` input picks it (`blender36-full-arm64` / `blender36-lite-arm64`
artifacts). `lite` is round 20's configuration and is kept only as a known-good
bisect target.

`full` enables Cycles (CPU, Embree), USD, Alembic, OpenVDB, OpenSubdiv,
OpenImageDenoise, Collada, Potrace, Boost, OpenXR and FFmpeg. Collada needs
`WITH_OPENCOLLADA`; `WITH_COLLADA` is not a 3.6 CMake option and is silently
ignored, which is why rounds up to 40 reported `collada=False`. Two things are
still off, for dependency reasons rather than choice:

- **OpenShadingLanguage.** 3.6's OSL glue targets OSL 1.12 / LLVM 15; the only
  ARM64 libraries available are OSL 1.13 / LLVM 17, so Cycles would need a
  port, not a flag.
- **Draco.** There is no `draco` directory in the 4.2 ARM64 dependency set at
  all, so glTF compression stays unavailable (`Draco mesh compression is not
  available` is logged, and glTF still exports everything else).

GPU device backends stay off on purpose: there are no CUDA/OptiX/HIP/oneAPI/
Metal drivers on Windows ARM64, and 4.2 disables CUDA/HIP there too.
`WITH_TBB_MALLOC_PROXY` is off because TBB's allocator replacement is
unsupported on ARM64.

Two library ABI drifts are being carried rather than avoided, and are the parts
to suspect if the full build misbehaves: **OpenVDB 11.0** (3.6 expects 10.0) and
**USD 24.05** (3.6's code targets 23.05, and the shipped `usd_ms.lib` was built
against Python 3.11 while this tree links Python 3.10 — the C API symbol names
it needs are version-independent, so this may link, but it is unproven).

USD's Python bindings are unusable here for the same reason, and `0025` opts the
`bf_usd` target out of them: the prebuilt USD defines
`PXR_PYTHON_SUPPORT_ENABLED` in `pxr/pxr.h`, so `tf/pyObjWrapper.h` includes
`boost/python`, while the dependency set only has `boost_python311` for its
Python 3.11. Blender's USD I/O never calls USD's Python API, and USD's own
static asserts guarantee the stub `TfPyObjWrapper` it uses instead has identical
size and alignment. Boost itself is otherwise linked dynamically (`0024` keys
the `BOOST_ALL_DYN_LINK` detection on `boost_locale`, because the
`boost_python310` file 3.6 looks for does not exist in a 3.11-built set).

`numpy` is now compiled from the sdist (`ci_numpy_arm64.bat`) because no
`win_arm64`/cp310 wheel exists for 1.26.4 or 2.x; a headers-only numpy made
`import numpy` succeed as an empty namespace package, which is why FBX and glTF
export failed on the lite artifact with `module 'numpy' has no attribute
'single'`.

## 4. Not verified

- The GUI was driven on the SQ2 only for a startup scene (round-20 tree): it
  opens, draws the cube, grid, gizmos and header icons. Toolbar tool icons were
  blank there until `datafiles/icons` was restored; rendering, navigation
  smoothness and heavier scenes on the Adreno GPU are still unmeasured.
- The lite set means nothing Cycles/USD/FFmpeg/OpenVDB-related is measured.
- **The lite artifact's numpy is a stub.** `import numpy` succeeds there as an
  empty namespace package (headers only), so FBX export, glTF export and any
  add-on using numpy fail. The full build compiles a real numpy; that behaviour
  is what the CI smoke test now asserts (`NUMPYOK … True True`).
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
- A *linking* install also differs from a *complete* one: `cmake --install`
  stops at the first `install(FILES ...)` whose source does not exist and skips
  every later rule without failing the build. Round 20 lost `datafiles/icons`
  and `datafiles/studiolights` that way, because 3.6 still names
  `libsndfile-1.dll` while the 4.2 arm64 set ships `sndfile.dll`. `0012` guards
  that rule and the staging step now requires both directories.
- `WITH_PYTHON_INSTALL=OFF` (the first lite configuration) produces a tree with
  no `3.6/python` at all: the exe starts, prints `--version`, and then dies on
  `ModuleNotFoundError: No module named 'encodings'` as soon as Python
  initialises — which is to say, for the bridge, immediately. The workflow now
  installs Python and checks that `encodings` and `bpy` import.
