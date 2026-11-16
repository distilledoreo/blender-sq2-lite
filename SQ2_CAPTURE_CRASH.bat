@echo off
REM Re-run the screenshot test but SAVE the GPU debug log so a crash names the failing shader.
setlocal
set MESA_GL_VERSION_OVERRIDE=4.3
set MESA_GLSL_VERSION_OVERRIDE=430
set GALLIUM_DRIVER=d3d12
set LOGDIR=%TEMP%\blender\debug_logs
mkdir "%LOGDIR%" >NUL 2>&1
del "%LOGDIR%\sq2_crash_run_out.txt" >NUL 2>&1
del "%LOGDIR%\sq2_crash_run_err.txt" >NUL 2>&1
echo Launching Gen2-lift + Mesa + override, logging to %LOGDIR%\sq2_crash_run_*.txt ...
echo If it crashes: send me sq2_crash_run_out.txt (has the shader compile error) + blender.crash.txt.
echo.
C:\blender-sq2-gen2\blender.exe --factory-startup --debug --debug-gpu --log cycles > "%LOGDIR%\sq2_crash_run_out.txt" 2> "%LOGDIR%\sq2_crash_run_err.txt"
echo Blender exited with code %ERRORLEVEL%.
echo --- last 40 lines of stdout log ---
powershell -NoProfile -Command "Get-Content $env:TEMP\blender\debug_logs\sq2_crash_run_out.txt -Tail 40"
