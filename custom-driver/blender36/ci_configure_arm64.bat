@echo off
rem Configure Blender 3.6 for native Windows ARM64 with Ninja.
rem Must run inside a vcvarsall arm64 environment: the "Visual Studio 17 2022"
rem generator cannot find a VS instance on the arm64 CI runner, so Ninja + cl is
rem used, the same path the 5.2 arm64 build takes.
rem
rem Usage: ci_configure_arm64.bat <src> [full|lite]
rem   full (default) builds Cycles, USD, Alembic, OpenVDB, OpenSubdiv,
rem   OpenImageDenoise, Collada, Potrace, Boost, OpenXR and FFmpeg. The only
rem   option left off is OpenShadingLanguage, whose 3.6 code targets OSL 1.12 /
rem   LLVM 15 while the arm64 dependency set ships OSL 1.13 / LLVM 17, and Draco,
rem   which has no library in the arm64 dependency set at all.
rem   lite is the round-20 feature set (EEVEE/Workbench only), kept so a
rem   regression can be bisected against a known-good configuration.
setlocal
set "SRC=%~1"
if "%SRC%"=="" set "SRC=C:\b"
set "FEATURES=%~2"
if "%FEATURES%"=="" set "FEATURES=full"

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

rem Common: packaging and the locally-built numpy (no arm64 wheel exists), and
rem no system-wide module search so the tree is self-contained.
rem
rem WITH_TBB_MALLOC_PROXY is off because TBB's allocator replacement is not
rem supported on Windows ARM64 (it prints "skip allocation functions
rem replacement in ucrtbase.dll" and does nothing).
set "COMMON=-DWITH_PYTHON_INSTALL=ON -DWITH_PYTHON_INSTALL_NUMPY=OFF -DWITH_DRACO=OFF -DWITH_TBB_MALLOC_PROXY=OFF -DWITH_WINDOWS_FIND_MODULES=OFF -DWITH_FFMPEG=ON"

if /I "%FEATURES%"=="lite" goto :lite
if /I "%FEATURES%"=="full" goto :full
echo Unknown feature set "%FEATURES%", expected full or lite.
exit /b 4

:full
rem GPU device backends are all off: there are no CUDA/OptiX/HIP/oneAPI/Metal
rem drivers on Windows ARM64 (upstream 4.2 disables CUDA/HIP the same way).
rem Cycles CPU still gets Embree, whose arm64 build is SSE/AVX code through
rem sse2neon-compiled kernels in Blender's own sources (patches 0013/0014).
set "OPTS=-DWITH_CYCLES=ON -DWITH_CYCLES_OSL=OFF -DWITH_CYCLES_EMBREE=ON -DWITH_CYCLES_DEVICE_CUDA=OFF -DWITH_CYCLES_DEVICE_OPTIX=OFF -DWITH_CYCLES_DEVICE_HIP=OFF -DWITH_CYCLES_DEVICE_ONEAPI=OFF -DWITH_CYCLES_DEVICE_METAL=OFF -DWITH_CYCLES_STANDALONE=OFF -DWITH_OPENIMAGEDENOISE=ON -DWITH_OPENVDB=ON -DWITH_OPENVDB_BLOSC=OFF -DWITH_OPENSUBDIV=ON -DWITH_ALEMBIC=ON -DWITH_USD=ON -DWITH_COLLADA=ON -DWITH_OPENCOLLADA=OFF -DWITH_POTRACE=ON -DWITH_BOOST=ON -DWITH_XR_OPENXR=ON"
goto :configure

:lite
set "OPTS=-DWITH_CYCLES=OFF -DWITH_USD=OFF -DWITH_ALEMBIC=OFF -DWITH_OPENIMAGEDENOISE=OFF -DWITH_OPENVDB=OFF -DWITH_OPENSUBDIV=OFF -DWITH_COLLADA=OFF -DWITH_OPENCOLLADA=OFF -DWITH_POTRACE=OFF -DWITH_BOOST=OFF -DWITH_HYDRA=OFF -DWITH_XR_OPENXR=OFF -DWITH_PYTHON_INSTALL_NUMPY=OFF"
goto :configure

:configure
cmake -S "%SRC%" -B "%SRC%\build" -G Ninja -DCMAKE_BUILD_TYPE=Release %COMMON% %OPTS%
exit /b %ERRORLEVEL%
