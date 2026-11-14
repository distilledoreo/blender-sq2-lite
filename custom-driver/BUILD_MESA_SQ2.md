## Build baseline Mesa for Windows ARM64 (your fork starting point)

Do this on a fast machine with VS2022 17.9+ (ARM64 tools) + Windows SDK 20348+.

Mesa docs: https://docs.mesa3d.org/install.html — MSVC ARM64/AARCH64 supported, Meson required, Python 3.10+ + Mako + Flex/Bison (Win flex-bison) required.

### 1. Get source (26.2.x tested Feb 2026)

```
git clone https://gitlab.freedesktop.org/mesa/mesa.git -b 26.2 mesa-sq2
cd mesa-sq2
pip install mako packaging
# install Win flex-bison, add to PATH
# install Meson + Ninja + CMake + DirectX-Headers (auto via wrap fallback >=1.611.0)
```

### 2. Configure — Windows auto drivers are llvmpipe/softpipe/zink/d3d12

```
meson setup build-windows-aarch64 `
  --backend ninja `
  -D gallium-drivers=d3d12,zink,llvmpipe `
  -D vulkan-drivers=swrast `
  -D microsoft-clc=disabled `
  -D gallium-d3d12-video=disabled `
  -D platforms=windows `
  -D directx-headers=enabled
```

Why this combo:
- `d3d12` = OpenGL 3.3 on D3D12 (hardware, works on Gen2 D3D12 path). Proves submission works.
- `zink` = OpenGL on Vulkan. Pair with Dozen (Vulkan-on-D3D12) or Lavapipe to test GL 4.x path.
- `llvmpipe` = CPU reference to compare against (your "too slow" baseline).

Build: `ninja -C build-windows-aarch64`

Output you care about: `build-windows-aarch64/src/gallium/targets/libgl-gdi/opengl32.dll`

### 3. Test app-local (no install, no signing)

```
mkdir C:\blender-sq2\mesa-test\
copy build-windows-aarch64\src\gallium\targets\libgl-gdi\opengl32.dll C:\blender-sq2\mesa-test\
copy "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" C:\blender-sq2\mesa-test\  # or portable
# Windows loads opengl32.dll from app dir first with .local redirection:
type nul > C:\blender-sq2\mesa-test\blender.exe.local
C:\blender-sq2\mesa-test\blender.exe --factory-startup --gpu-backend OPENGL --debug-gpu > mesa-test.txt 2>&1
```

Epoxy loads system GL — `.local` + app-dir DLL is how you override without touching System32 or Secure Boot.

### 4. Expectation (honest)

Stock Mesa d3d12 gives you GL 3.3 only → Blender 5.2 still says Unsupported. That's expected.
It proves your build + loader works. The actual SQ2 fix is the shim in `shim/sq2_gl_shim.c`:
fork `src/mesa/main/version.c` + `src/gallium/drivers/d3d12` to report 4.3 LIMITED + CPU-emulate the 2 extensions for Workbench draws only.

Full EEVEE via this path will still be black — typed-UAV gap is in Qualcomm KMD, not in Mesa. Keep startup file on Solid.
