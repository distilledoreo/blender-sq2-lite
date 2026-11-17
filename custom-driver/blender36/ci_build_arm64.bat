@echo off
rem Build the configured Blender 3.6 ARM64 tree with Ninja.
setlocal
set "SRC=%~1"
if "%SRC%"=="" set "SRC=C:\b"

for /f "usebackq delims=" %%i in (`vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.ARM64 -property installationPath`) do set "VSPATH=%%i"
if "%VSPATH%"=="" (
  echo No Visual Studio instance with ARM64 tools found.
  exit /b 2
)
call "%VSPATH%\VC\Auxiliary\Build\vcvarsall.bat" arm64
if errorlevel 1 exit /b 3

cmake --build "%SRC%\build"
exit /b %ERRORLEVEL%
