@echo off
rem Build numpy for the injected ARM64 CPython 3.10.
rem
rem No win_arm64 / cp310 wheel exists on PyPI (numpy 1.26.4 and 2.x both return
rem "No matching distribution"), so the sdist is compiled with the same ARM64
rem MSVC toolchain as Blender. It installs into the libdir's site-packages,
rem which `cmake --install` copies into <install>/3.6/python/lib.
rem
rem numpy 1.26.4 is a *meson* package (build-backend = "mesonpy"), which is why
rem the build deps below are meson/meson-python rather than setuptools: with
rem `--no-build-isolation` pip does not fetch them itself, and the isolated
rem variant cannot work here because the Cython 0.29 line that numpy's
rem pyproject also allows has no win_arm64 wheel. meson detects the ARM64
rem compiler from the vcvarsall environment, and numpy's `allow-noblas` option
rem already defaults to true, which is what we need since the dependency set
rem ships no BLAS.
rem
rem A real numpy is required at runtime, not just its headers: FBX export dies
rem on numpy.single, and any add-on using numpy gets an empty namespace package
rem if only numpy/core/include is present.
setlocal
set "SRC=%~1"
if "%SRC%"=="" set "SRC=C:\b"
set "PYDIR=%SRC%\lib\windows_arm64\python\310"
set "PY=%PYDIR%\bin\python.exe"
rem pip installs console scripts (cython.exe, meson.exe) into Scripts, and meson
rem looks Cython up by running `cython -V` on PATH, so that directory has to be
rem on PATH for the numpy build to configure at all.
set "PATH=%PYDIR%\Scripts;%PYDIR%;%PATH%"

for /f "usebackq delims=" %%i in (`vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.ARM64 -property installationPath`) do set "VSPATH=%%i"
if "%VSPATH%"=="" (
  echo No Visual Studio instance with ARM64 tools found.
  exit /b 2
)
call "%VSPATH%\VC\Auxiliary\Build\vcvarsall.bat" arm64
if errorlevel 1 (
  echo vcvarsall arm64 failed.
  exit /b 3
)

rem meson-python drives ninja; the runner image provides it, but say so loudly
rem rather than failing later inside meson with a confusing message.
where ninja
if errorlevel 1 (
  echo ninja is required by meson-python and is not on PATH.
  exit /b 4
)

rem distutils only uses the already-set-up environment (no vcvars re-detection).
set "DISTUTILS_USE_SDK=1"
set "MSSdk=1"

"%PY%" -m pip install --no-cache-dir --disable-pip-version-check --only-binary=:all: ^
  "setuptools>=68" wheel "packaging>=23.2" "Cython<3.1" "meson==1.3.2" "meson-python==0.15.0"
if errorlevel 1 exit /b 5

"%PY%" -m pip install --no-cache-dir --disable-pip-version-check --no-build-isolation --no-binary=:all: "numpy==1.26.4"
if errorlevel 1 exit /b 6

"%PY%" -c "import numpy, numpy.core.multiarray; print('NUMPY', numpy.__version__, numpy.single)"
exit /b %ERRORLEVEL%
