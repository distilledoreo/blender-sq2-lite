@echo off
rem Launch Blender 3.6 with the SQ2 legacy bridge active.
rem
rem   tools\blender36\blender36.cmd scene.blend
rem   tools\blender36\blender36.cmd -b scene.blend --python script.py
rem
rem Set BLENDER36_HOME to point at another 3.6 install (the folder that holds
rem blender.exe). Files are assumed to be 4.5: they open natively, the bridge
rem records the engine name and view transform 3.6 had to substitute, and every
rem save is rewritten as a 4.5 file by BLENDER45_EXE.
setlocal
set "HERE=%~dp0"

rem The 4.5 binary that turns each 3.6 save back into a 4.5 file. Override with
rem BLENDER45_EXE if 4.5 lives somewhere else. The ARM64 build comes first: this
rem launcher exists for the SQ2, and an x64 4.5 only works there through
rem emulation.
if "%BLENDER45_EXE%"=="" if exist "%HERE%..\..\blender-4.5.16-windows-arm64\blender.exe" set "BLENDER45_EXE=%HERE%..\..\blender-4.5.16-windows-arm64\blender.exe"
if "%BLENDER45_EXE%"=="" if exist "%HERE%..\..\blender-4.5.16-windows-x64\blender.exe" set "BLENDER45_EXE=%HERE%..\..\blender-4.5.16-windows-x64\blender.exe"

rem The ARM64 3.6 build is the one to use on the SQ2; the x64 tree is only a
rem fallback for a machine that cannot run ARM64 binaries.
if "%BLENDER36_HOME%"=="" if exist "%HERE%..\..\blender-3.6.23-windows-arm64\blender.exe" set "BLENDER36_HOME=%HERE%..\..\blender-3.6.23-windows-arm64"
if "%BLENDER36_HOME%"=="" set "BLENDER36_HOME=%HERE%..\..\blender-3.6.23-windows-x64"

if not exist "%BLENDER36_HOME%\blender.exe" (
  echo BLENDER36_HOME does not contain blender.exe: %BLENDER36_HOME%
  echo Set BLENDER36_HOME to the Blender 3.6 install folder and retry.
  exit /b 1
)

rem Keep the bridge in sync with the repo copy (cheap, ~10 KB).
for /d %%D in ("%BLENDER36_HOME%\3.*") do (
  if exist "%%D\scripts" (
    copy /y "%HERE%bridge\sq2_legacy_bridge.py" "%%D\scripts\startup\sq2_legacy_bridge.py" >nul 2>&1
  )
)

"%BLENDER36_HOME%\blender.exe" %*
exit /b %ERRORLEVEL%
