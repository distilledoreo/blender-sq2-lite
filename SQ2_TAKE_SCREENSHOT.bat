@echo off
REM SQ2 screenshot test: Gen2-lift Blender + Mesa d3d12 + GL 4.3 override.
REM Double-click this file. Blender will open (click through any "Limited Platform Support" dialog).
setlocal
set MESA_GL_VERSION_OVERRIDE=4.3
set MESA_GLSL_VERSION_OVERRIDE=430
set GALLIUM_DRIVER=d3d12
echo Mesa DLLs beside exe:
dir C:\blender-sq2-gen2\opengl32.dll C:\blender-sq2-gen2\libEGL.dll
echo.
echo Launching C:\blender-sq2-gen2\blender.exe --factory-startup --debug-gpu ...
echo 1. Wait for the window. If a "Limited Platform Support" box appears, click past it.
echo 2. You should see the default cube in Solid (grey) mode.
echo 3. Orbit: hold MIDDLE mouse button and drag. Zoom: mouse wheel.
echo 4. Screenshot: press Win+Shift+S, drag over the Blender window, paste/save the image.
echo 5. Send me that screenshot + tell me if it stayed open or closed.
echo.
C:\blender-sq2-gen2\blender.exe --factory-startup --debug-gpu
