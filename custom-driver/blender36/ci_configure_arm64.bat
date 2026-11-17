@echo off
rem Configure Blender 3.6 for native Windows ARM64 (lite) with Ninja.
rem Must run inside a vcvarsall arm64 environment: the "Visual Studio 17 2022"
rem generator cannot find a VS instance on the arm64 CI runner, so Ninja + cl is
rem used, the same path the 5.2 arm64 build takes.
setlocal
set "SRC=%~1"
if "%SRC%"=="" set "SRC=C:\b"

for /f "usebackq delims=" %%i in (`vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.ARM64 -property installationPath`) do set "VSPATH=%%i"
echo VSPATH=%VSPATH%
if "%VSPATH%"=="" (
  echo No Visual Studio instance with ARM64 tools found.
  exit /b 2
)
call "%VSPATH%\VC\Auxiliary\Build\vcvarsall.bat" arm64
if errorlevel 1 (
  echo vcvarsall arm64 failed.
  exit /b 3
)
echo ---- cl ----
where cl

cmake -S "%SRC%" -B "%SRC%\build" -G Ninja -DCMAKE_BUILD_TYPE=Release ^
  -DWITH_CYCLES=OFF -DWITH_USD=OFF -DWITH_ALEMBIC=OFF ^
  -DWITH_OPENIMAGEDENOISE=OFF -DWITH_FFMPEG=OFF -DWITH_OPENVDB=OFF ^
  -DWITH_OPENSUBDIV=OFF -DWITH_COLLADA=OFF -DWITH_OPENCOLLADA=OFF -DWITH_POTRACE=OFF ^
  -DWITH_BOOST=OFF -DWITH_HYDRA=OFF -DWITH_XR_OPENXR=OFF ^
  -DWITH_PYTHON_INSTALL=ON -DWITH_PYTHON_INSTALL_NUMPY=OFF -DWITH_DRACO=OFF ^
  -DWITH_WINDOWS_FIND_MODULES=OFF
exit /b %ERRORLEVEL%
