@echo off
rem Prints the DLL imports of the freshly built arm64 blender.exe.
rem dumpbin comes with the ARM64 MSVC toolset, so vcvarsall arm64 must be set up.
setlocal

set "SRC=%~1"
if "%SRC%"=="" (
  echo usage: ci_stage_arm64.bat ^<build root^>
  exit /b 2
)
if not exist "%SRC%\build\bin\blender.exe" (
  echo blender.exe not found under "%SRC%\build\bin"
  exit /b 3
)

set "VSWHERE=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
if not exist "%VSWHERE%" (
  echo vswhere not found
  exit /b 4
)

set "VSPATH="
for /f "usebackq delims=" %%i in (`"%VSWHERE%" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.ARM64 -property installationPath`) do set "VSPATH=%%i"
if not defined VSPATH (
  echo no Visual Studio with ARM64 tools found
  exit /b 5
)

call "%VSPATH%\VC\Auxiliary\Build\vcvarsall.bat" arm64
if errorlevel 1 exit /b 6

dumpbin /nologo /dependents "%SRC%\build\bin\blender.exe"
exit /b %ERRORLEVEL%
