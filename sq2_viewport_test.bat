@echo off
REM SQ2 viewport test - tries Blender 5 ARM GUI with different GPU backends
REM Logs go to .\logs\
REM Edit the line below WITHOUT quotes: set BLENDER_EXE=C:\path\to\blender.exe

setlocal EnableDelayedExpansion
mkdir logs 2>nul

REM Hard-coded path (no quotes here - quotes added at use time)
set BLENDER_EXE=C:\Program Files\Blender Foundation\Blender 5.2\blender.exe
if defined BLENDER_EXE_OVERRIDE set BLENDER_EXE=%BLENDER_EXE_OVERRIDE:"=%
set BLENDER_EXE=%BLENDER_EXE:"=%

if not exist "%BLENDER_EXE%" (
  echo Not found: "%BLENDER_EXE%"
  echo Trying auto-detect...
  set BLENDER_EXE=
)

if not defined BLENDER_EXE (
  for /f "delims=" %%p in ('where blender.exe 2^>nul') do (
    if not defined BLENDER_EXE set BLENDER_EXE=%%p
  )
)
if not defined BLENDER_EXE (
  if exist "C:\Program Files\Blender Foundation\Blender 5.3\blender.exe" set BLENDER_EXE=C:\Program Files\Blender Foundation\Blender 5.3\blender.exe
)
if not defined BLENDER_EXE (
  if exist "C:\Program Files\Blender Foundation\Blender\blender.exe" set BLENDER_EXE=C:\Program Files\Blender Foundation\Blender\blender.exe
)
REM Portable layout: .\blender-5*-windows-arm64\blender.exe
for /d %%d in (blender-*-windows-arm64) do (
  if exist "%%d\blender.exe" set BLENDER_EXE=%CD%\%%d\blender.exe
)

if not defined BLENDER_EXE (
  echo Could not find blender.exe.
  echo Edit this .bat: set BLENDER_EXE=C:\path\to\blender.exe  (no quotes)
  echo Or: set BLENDER_EXE_OVERRIDE=C:\path\to\blender.exe
  pause
  exit /b 1
)

echo Using: "%BLENDER_EXE%"
"%BLENDER_EXE%" --version > logs\version.txt 2>&1
type logs\version.txt

echo.
echo --- Test 1: factory startup, OpenGL backend ---
"%BLENDER_EXE%" --factory-startup --gpu-backend OPENGL --debug-gpu > logs\test1-opengl.txt 2>&1

echo --- Test 2: factory startup, Vulkan backend ---
"%BLENDER_EXE%" --factory-startup --gpu-backend VULKAN --debug-gpu > logs\test2-vulkan.txt 2>&1

echo --- Test 3: force workarounds (disables all GPU extensions) ---
"%BLENDER_EXE%" --factory-startup --debug-gpu-force-workarounds --debug-gpu > logs\test3-workarounds.txt 2>&1

echo --- Test 4: Vulkan + force workarounds ---
"%BLENDER_EXE%" --factory-startup --gpu-backend VULKAN --debug-gpu-force-workarounds --debug-gpu > logs\test4-vulkan-workarounds.txt 2>&1

echo.
echo Done. Check logs\test*.txt for "Unsupported Graphics Card" vs successful window.
echo If all 4 still show the Unsupported dialog, see README_SQ2.md WARP fallback.
pause
