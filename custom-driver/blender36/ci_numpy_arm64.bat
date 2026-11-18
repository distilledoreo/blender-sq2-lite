@echo off
rem Build numpy for the injected ARM64 CPython 3.10.
rem
rem No win_arm64 / cp310 wheel exists on PyPI (checked: numpy 1.26.4 and 2.x both
rem return "No matching distribution"), so the sdist is compiled with the same
rem ARM64 MSVC toolchain as Blender. It installs straight into the libdir's
rem site-packages, which `cmake --install` copies into <install>/3.6/python/lib.
rem
rem A real numpy is required at runtime, not just its headers: FBX export dies on
rem numpy.single, and any add-on using numpy gets an empty namespace package if
rem only numpy/core/include is present.
setlocal
set "SRC=%~1"
if "%SRC%"=="" set "SRC=C:\b"
set "PYDIR=%SRC%\lib\windows_arm64\python\310"

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

rem distutils only uses the already-set-up environment (no vcvars re-detection).
set "DISTUTILS_USE_SDK=1"
set "MSSdk=1"

"%PYDIR%\bin\python.exe" -m pip install --no-cache-dir --no-binary=:all: "numpy==1.26.4"
if errorlevel 1 exit /b 4

"%PYDIR%\bin\python.exe" -c "import numpy, numpy.core.multiarray; print('NUMPY', numpy.__version__, numpy.single)"
exit /b %ERRORLEVEL%
