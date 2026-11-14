@echo off
REM SQ2 outside-the-box bridge: headless Blender 5.2 (works) -> glTF -> Three.js (hardware-fast in Edge/Chrome)
REM Usage: bridge.bat C:\path\to\latest.blend
setlocal
set BLEND=%~1
if "%BLEND%"=="" (
  echo Usage: bridge.bat C:\path\to\latest.blend
  pause
  exit /b 1
)
set BLENDER_EXE=C:\Program Files\Blender Foundation\Blender 5.2\blender.exe
if defined BLENDER_EXE_OVERRIDE set BLENDER_EXE=%BLENDER_EXE_OVERRIDE:"=%
set BLENDER_EXE=%BLENDER_EXE:"=%
if not exist "%BLENDER_EXE%" (
  echo Edit bridge.bat: set BLENDER_EXE to your blender.exe path
  pause
  exit /b 1
)
set OUT=%~dp0sq2_preview.glb
echo Exporting %BLEND% via headless Blender...
"%BLENDER_EXE%" -b "%BLEND%" --python "%~dp0export_gltf.py" -- "%OUT%"
if not exist "%OUT%" (
  echo Export failed. Check Blender headless output above.
  pause
  exit /b 1
)
echo.
echo Opening hardware-fast WebGL viewport...
start "" "%~dp0view.html"
echo Now drag sq2_preview.glb into the page if it didn't auto-load.
echo Edit in web: inspect proportions, cameras, staging at full speed on SQ2.
echo For real mesh edits, use 3.6 LTS locally or remote Blender, then re-export.
pause
