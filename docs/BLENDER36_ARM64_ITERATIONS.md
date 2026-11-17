# Blender 3.6 Windows-ARM64: CI iteration log

Workflow: `.github/workflows/blender36-arm64.yml` (`blender36-arm64-lite`),
runner `windows-11-arm`, Ninja + `vcvarsall arm64`.

Setup per run: clone Blender `v3.6.23` → clone `lib-windows_arm64`
(`blender-v4.2-release`) into `lib/windows_arm64` → inject ARM64 CPython
3.10.11 (nuget `pythonarm64`) at `lib/windows_arm64/python/310` → apply
`custom-driver/blender36/*.patch` → configure lite → build.

| # | run | first failure | cause | fix |
|---|-----|---------------|-------|-----|
| 1 | 44110093352 | configure: `Generator Visual Studio 17 2022 could not find any instance of Visual Studio` | the arm64 runner has VS 2026 (Build Tools/Enterprise) and the VS generator does not accept it; the 5.2 arm64 build uses Ninja | configure with `-G Ninja` inside `vcvarsall arm64` (`ci_configure_arm64.bat`) |
| 2 | — | workflow file invalid (YAML) | batch heredoc was written at column 1 inside a YAML block scalar | moved the batch logic into `custom-driver/blender36/ci_*.bat` |
| 3 | 44111743714 | `ninja: error: libgmp-10.lib missing` | arm64 dep set ships `gmp.dll.lib` | patch hunk 5 in `0001-windows-arm64-build-support.patch` |
| 4 | 44114093421 | `ninja: error: libfftw.lib missing` | 3.6 knows `libfftw3-3.lib` (3.3) and `libfftw.lib` (3.5); the arm64 set uses `fftw3.lib`/`fftw3f.lib` | patch hunk 6: `elseif(EXISTS ${FFTW3}/lib/fftw3.lib)` |
| 5 | 44115308225 | `ninja: error: opencollada/lib/opencollada/pcre.lib missing` | OpenCOLLADA's bundled pcre is absent from the arm64 set | `-DWITH_OPENCOLLADA=OFF` (lite) |
| 6 | 44116466381 | `ninja: error: libsndfile-1.lib missing` | arm64 set ships `sndfile.lib`; 3.6 referenced it through the `${LIBSNDFILE_LIBPATH}` alias, so the literal scan missed it | patch hunk 7: `if(EXISTS ...libsndfile-1.lib) else sndfile.lib` |
| 7 | 44117699207 | `GHOST_SystemWin32.cc: error C2059: syntax error: ')'` ×13 | `WINTAB_PRINTF(x, ...)` expands to `printf(x, __VA_ARGS__)`; calls with a format string only become `printf(x, )`, which `/Zc:preprocessor` (mandatory for sse2neon) rejects | `0002-ghost-wintab-printf-conforming-preprocessor.patch`, same `_MSVC_TRADITIONAL` split upstream 4.2 uses |
| 8 | 44119916610 | `extern/lzo/minilzo/lzodefs.h: #error FIXME - missing LZO_OS_WIN64 define for CPU architecture` | LZO detects ARM64 only via `__aarch64__`, never `_M_ARM64` | `0003-lzo-arch-arm64-msvc.patch` |
| 9 | 44127891836 | step *Inject ARM64 Python 3.10*: `numpy sdist not downloaded` | no cp310/win_arm64 numpy wheel exists; `pip download --no-binary=:all:` built metadata for 5 min and left no `.tar.gz` | take the arch-independent `numpy/core/include` from the `win_amd64` wheel instead of an sdist |
| 10 | 44130007352 | `interface_template_asset_view.cc(184): error C2059: syntax error: ')'` ×7 | `RNA_warning(format, ...)` expands to `_RNA_warning(..., __FUNCTION__, __VA_ARGS__)`; a format-only call leaves `, )`. The traditional MSVC preprocessor drops that comma, `/Zc:preprocessor` (from `0001`) does not. Every other `__VA_ARGS__` macro in the tree either takes a real first argument or is a `VA_NARGS` overload, so `RNA_warning` was the only remaining case (9 call sites). | `0004-rna-warning-empty-varargs-conforming-preprocessor.patch`, `_MSVC_TRADITIONAL` split like `0002`; reproducing locally with MSVC 14.51 gives the identical `error C2059` for the old form and no error for the new one |

| 11 | 44137370636 | `blenlib/intern/system.c(126): error C4013: '__cpuid' undefined; assuming extern returning int` | `BLI_cpu_brand_string()` / `BLI_cpu_support_sse41()` call MSVC's `__cpuid` intrinsic, which only exists for x86; 3.6 has no ARM guard | `0005-blenlib-cpuid-x86-only.patch`: `#if !defined(_M_ARM64)` around both CPUID blocks, the CPU brand falls back to the registry `VendorIdentifier` (`advapi32` is already in the 3.6 Windows link list), SSE4.1 reports 0; same shape as upstream 4.2 |

| 12 | 44144435107 | `system_win32.c(145): error C2039: 'Rip': is not a member of '_CONTEXT'` and `BKE_customdata.h(687): error C2220` (warning C5287) | crash backtrace read the x64 register names `Rip`/`Rsp` and always walked as `IMAGE_FILE_MACHINE_AMD64`; and the `CD_FAKE_*` layer ids OR the `CD_FAKE` int enum with `eCustomDataType` enum values, which MSVC 14.4x warns about and `/WX` turns into an error | `0006`: `_M_AMD64`/`_M_ARM64` split using `Pc`/`Fp`/`Sp` and `IMAGE_FILE_MACHINE_ARM64`, copied from upstream 4.2; `0007`: `(int)` casts on the four mixed-type values, verified locally against MSVC 14.51 (`C5287` reproduces without the cast, absent with it) |

Progress markers: run 7 reached `[1746/4757]` objects before the GHOST error,
run 8 reached `[2029/4757]`, run 10 reached `[2432/4757]`, run 11 reached
`[3429/4757]`, run 12 reached `[3449/4757]`.

Reusable helpers:

- `ci_configure_arm64.bat` / `ci_build_arm64.bat` — vcvarsall arm64 + cmake.
- The patch set is applied by glob, so new patches are picked up automatically.

Standing lite option set: `WITH_CYCLES/USD/ALEMBIC/OPENIMAGEDENOISE/FFMPEG/
OPENVDB/OPENSUBDIV/COLLADA/OPENCOLLADA/POTRACE/BOOST/HYDRA/XR_OPENXR=OFF`,
`WITH_PYTHON_INSTALL=OFF`. Cycles and the importers are the "full" round,
added after lite links.
