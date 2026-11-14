Blender 5 on SQ2 (Snapdragon 8cx Gen2 / Adreno 690) - why headless works but GUI doesn't, and what to try for a modeling viewport.

## Why you see this

- Headless (`blender -b`) skips the viewport OpenGL context init. Cycles CPU rendering works, so latest .blend files load and render natively on ARM. That's why headless works.
- GUI startup creates an OpenGL 4.3 context. On Windows-on-Arm this goes through Mesa GLOn12 -> Qualcomm D3D12 driver. Blender >=4.0 dropped 8cx Gen2 and older because of unfixed driver bugs. Active support for those drivers has ended.
- Your "Unsupported Graphics Card Configuration / OpenGL 4.3 or higher is required" dialog is that check failing, not a missing ARM build.

Linaro write-up: https://www.linaro.org/blog/blender-now-enabled-on-windows-on-arm
Blender WoA announcement (4.3 first, 4.5 LTS Vulkan): https://code.blender.org/2025/08/blender-for-windows-on-arm

No DLL Frankenstein fixes this - Linaro already tried ARM64EC mixing and abandoned it as impractical. The viewport + 70 native deps move together.

## What to try, in order

### 1. Run sq2_viewport_test.bat (in this folder)

It auto-finds `blender.exe` (PATH, Program Files, or a `blender-*-windows-arm64` portable folder placed here) and tries:

1. `--gpu-backend OPENGL`
2. `--gpu-backend VULKAN`
3. `--debug-gpu-force-workarounds` (disables all GPU extensions)
4. `--gpu-backend VULKAN --debug-gpu-force-workarounds`

This last combo fixed GUI startup for some Windows 11 users with the same dialog. Check `logs\test*.txt`.

To set Blender explicitly if auto-detect fails:

  set BLENDER_EXE_OVERRIDE=C:\Program Files\Blender Foundation\Blender 5.3\blender.exe
  sq2_viewport_test.bat

Also install these first:
- OpenCL, OpenGL, and Vulkan Compatibility Pack (Microsoft Store, installs Mesa GLOn12)
- Latest SQ2 / Surface Pro X drivers from Windows Update

### 2. WARP fallback (slow viewport, but native modeling)

If all 4 tests still show Unsupported, force Windows to use the software D3D12 driver (WARP / Microsoft Basic Render Driver). Mesa GLOn12 on top of WARP can expose OpenGL 4.3 where the Adreno 690 driver cannot.

- Device Manager > Display adapters > right-click Qualcomm Adreno 690 > Disable device > Reboot
- Launch Blender ARM portable again (Test 1)
- Re-enable when done if you need battery / video decode

Expect: viewport works, but orbit/sculpt is CPU-rendered and slow. EEVEE renders may crash (known even on X1-85 with Vulkan) - use Cycles CPU or Workbench/Solid viewport shading for modeling.

This is the only on-device path to a full Blender 5 modeling viewport on SQ2. There is no fixed GPU driver coming for Gen2.

### 3. Use what already works: headless for latest files

Since headless works, you already have native latest-file support for batch work:

  blender -b latest_file.blend -E CYCLES -f 1
  blender -b latest_file.blend -o converted_ --factory-startup -E CYCLES --python-expr "import bpy; bpy.ops.wm.save_as_mainfile(filepath='converted_45.blend')"

Model in Solid/Wireframe, avoid EEVEE viewport effects that need the broken driver path.

## Honest expectation

Full-speed EEVEE + GPU Cycles viewport on SQ2 with Blender 5 is not achievable - even Snapdragon X (Gen3+) needed Vulkan tiling work + native drivers for that, and EEVEE Vulkan render still crashes on X1-85 in some builds.

Best achievable on SQ2: software-GL modeling viewport (slow) + headless CPU Cycles renders/conversions (full speed for what the CPU can do). For real-time EEVEE work you need Gen3/X Elite or newer, or a second machine.
