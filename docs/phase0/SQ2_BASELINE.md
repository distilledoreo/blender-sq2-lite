# SQ2 Phase0 Baseline — 2026-11-16 (device: SQ2 / 8cx Gen2 / Adreno 680)

## GPU / Driver
- `Win32_VideoController`: Qualcomm(R) Adreno(TM) 680 GPU, Driver 27.20.2140.0, PNP `ACPI\VEN_QCOM&DEV_043A`
- Inbox `C:/Windows/System32/D3D12Core.dll` 6,235,552 bytes (Nov 11 OS version, pre-Agility opt-in)
- Inbox `vulkan-1.dll` 2,499,544 bytes (Oct 3)
- `HKLM\SOFTWARE\Khronos\Vulkan\Drivers` + WOW6432Node: **empty/missing** — no native Qualcomm Vulkan ICD registered
- `dxdiag /t` on this machine produced no output file in test (needs re-run via `dxdiag.exe` GUI); DirectX Caps Viewer / CheckFeatureSupport program still TODO

## Blender stock (C:/blender-sq2-lite, 5.2.3 LTS ARM64)
- `--version`: `Blender 5.2.3 LTS` OK
- `--factory-startup --debug-gpu --gpu-backend opengl --background`: prints version + `BLENDER_OK`, **no GPU lines** (background never creates GL context) — see `logs/phase0/blender_debug_gpu_opengl.txt`
- `--factory-startup --gpu-backend vulkan --background`:
  ```
  WARNING Device [Microsoft Direct3D12 (Qualcomm(R) Adreno(TM) 680 GPU)] does not meet minimum requirements. Missing features are [multi viewport, logical operations, dual source blending, buffer device address, VK_EXT_provoking_vertex]
  WARNING Device [Microsoft Direct3D12 (Microsoft Basic Render Driver)] does not meet minimum requirements. Missing features are [multi viewport, logical operations, dual source blending, VK_EXT_provoking_vertex]
  ERROR No Vulkan device found that meets the minimum requirements.
  ```
  → Enumerated devices are **Dzn (Vulkan-on-D3D12)**, not native Adreno Vulkan. Dzn = Vulkan 1.1 only, missing 1.3 `dynamic_rendering` + features above. Zink-over-native-Vulkan is blocked until a native ICD appears.

## Mesa current (mmozeiko/build-mesa 26.3.0 ARM64, 2026-11-10)
- `mesa-d3d12-arm64-26.3.0.7z` (2.58MB): `opengl32.dll` 16,542,208 bytes, `libEGL.dll` 16,569,344 bytes, Method `ARM64 LZMA2:25`
- `mesa-zink-arm64-26.3.0.7z` (2.63MB): `opengl32.dll` ~17MB, Method `ARM64 LZMA2:48m`
- Agility SDK `Microsoft.Direct3D.D3D12 1.619.5` downloaded: `build/native/bin/arm64/D3D12Core.dll` 4.8MB staged at `mesa-test/agility/`
- Issue mmozeiko#22: without app-local `D3D12Core.dll` (or without exe opting into Agility via `D3D12SDKVersion`/`D3D12SDKPath` exports) Mesa d3d12 exposes **GL 4.2 only** instead of 4.6. Stock `blender.exe` does NOT export Agility selectors, so inbox D3D12Core is used unless patched.

## Phase1 app-local test (2026-11-16)
- Setup: `mesa-test/d3d12/opengl32.dll` → `C:/blender-sq2-lite/opengl32.dll` (trusted exe path to avoid SmartScreen on copied exe), launch `blender.exe --factory-startup --debug-gpu --gpu-backend opengl` via `Start-Process`, wait 20s.
- Result: **GUI stayed running 20s** (`STILL_RUNNING_GUI_UP`, had to `Stop-Process`) vs stock instant quit with `Unsupported Graphics Card Configuration / OpenGL 4.3 or higher is required`. Only stderr line:
  ```
  GHOST_ContextWGL.cc:533: [GetLastError() == NO_ERROR] -> Win32 Error# (18): There are no more files.
  ```
  See `logs/phase1/blender_mesa_d3d12_gui_err.txt`. stdout empty (GUI log buffering — need official `--debug --debug-gpu --log cycles + sysinfo` pattern next).
- Gate decision (per plan): **keep `d3d12` path only, drop `zink`** — no native Vulkan ICD exists, Dzn is 1.1-only, double translation cannot meet Vulkan 1.3 + `VK_KHR_dynamic_rendering`.

## Next (Phase1 cont.)
1. Re-run with official debug pattern (`--debug --debug-gpu --log cycles + bpy.ops.wm.sysinfo`) to capture `blender_debug_output.txt` + `blender_system_info.txt` with Mesa d3d12 app-local.
2. Record GL version string via tiny WGL `GL_VERSION` probe (clangarm64) beside Mesa DLLs, inbox vs Agility `D3D12/` subdir.
3. Try `MESA_GL_VERSION_OVERRIDE=4.3` + `MESA_GLSL_VERSION_OVERRIDE=430` to find first real failure after context creation.
4. Visually confirm window: `Get-Process blender | Select MainWindowTitle` while running + user screenshot of Solid viewport.
