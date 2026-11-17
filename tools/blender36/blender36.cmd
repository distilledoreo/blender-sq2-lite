@echo off
rem Launch Blender 3.6 with the SQ2 legacy bridge active.
rem
rem   tools\blender36\blender36.cmd scene.blend
rem   tools\blender36\blender36.cmd -b scene.blend --python script.py
rem
rem Set BLENDER36_HOME to point at another 3.6 install (the folder that holds
rem blender.exe). Newer .blend files open natively; the bridge fixes the engine
rem name and view transform and reports anything 3.6 cannot represent.
setlocal
set "HERE=%~dp0"

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
