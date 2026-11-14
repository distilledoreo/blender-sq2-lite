# Frankenbuild: Blender 5.2 SQ2 Edition (hardware viewport, no EEVEE)

Goal you asked for: full modeling viewport on SQ2 itself, not WARP/software (too slow), with latest .blend file support.

## The trick

Don't mix 3.6 DLLs into 5.2. Instead build 5.2 from source with the Gen2 block removed and compute paths fenced off. File IO stays stock 5.2, so latest files open. Viewport stays on the Adreno hardware D3D12 path for simple draws (Solid/Wireframe), avoiding the broken compute/typed-UAV path that blocks EEVEE.

See `sq2_compat.patch` for the 3 edit locations in `source/blender/gpu/opengl/gl_backend.cc`.

## Steps (do this on a fast x64 or Snapdragon X machine, not the SQ2)

1. Install: VS2022 + ARM64 tools, CMake, Git, SVN.
2. Clone Blender 5.2 branch (tag `v5.2.3` or `blender-v5.2-release`):
   ```
   git clone https://projects.blender.org/blender/blender.git -b v5.2.3
   ```
3. Get prebuilt ARM64 libs (saves the 10hr dep build):
   ```
   cd blender
   make update
   ```
   This pulls `lib-windows_arm64` matching 5.2. Do NOT rebuild deps unless you have to.
4. Apply `sq2_compat.patch` by hand to `source/blender/gpu/opengl/gl_backend.cc` (line numbers shift, use search for `30.0.3820` and `epoxy_gl_version() >= 43`).
5. Configure a Lite test build first:
   ```
   make lite BUILD_DIR=build_lite
   ```
   If Lite opens a cube window on your test ARM machine, the patch applied cleanly.
6. Full build:
   ```
   make -j %NUMBER_OF_PROCESSORS% BUILD_DIR=build_sq2
   ```
7. Copy `build_sq2\bin\Release\` to SQ2 as portable folder. Launch:
   ```
   blender.exe --factory-startup --gpu-backend OPENGL
   ```
   Set startup file to Solid shading. Never switch to Material Preview / Rendered on SQ2.

## Rules for daily use on SQ2

- Model: Solid / Wireframe + Workbench only.
- Render: Cycles CPU (`-b file.blend -E CYCLES -f 1` - your headless path already works).
- EEVEE: off. It will be black/crash on Gen2 by design - that's the typed-UAV hardware gap, not a bug in your build.
- Keep a stock Blender 5.2 on another machine for EEVEE lookdev if you need it.

## Why this is the only "another way"

- 3.6 works because it needs GL 3.3. 5.x needs GL 4.3 + compute + SSBO>=12 + `GL_ARB_shader_draw_parameters` + `GL_ARB_clip_control`, Vulkan 1.3 + `VK_KHR_dynamic_rendering` (required since 5.0, optional in 4.5).
- Gen2 drivers cap at ~GL 4.2 via GLOn12 and lack typed UAV loads, so compute never arrives via driver update (support ended).
- Patching the version check alone without fencing compute = crash on first EEVEE draw. Fencing compute + staying in Workbench = hardware-speed modeling.

If you want, tell me your build machine OS and I'll tailor the exact `make` flags.
