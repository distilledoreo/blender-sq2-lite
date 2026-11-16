# Corrections to 2026-11-16 report (device-measured 2026-11-16)

1. Chip: **SQ2 confirmed** — `Win32_ComputerSystem Model: Surface Pro X`, `CPU: Microsoft SQ2 @ 3.15 GHz`. `Adreno 680` is the driver's name for the 8cx Gen2 GPU (earlier 690 notes were the marketing name). Baseline updated: SQ2, not SQ1.

2. True GL without override (WGL probe, Mesa d3d12 26.3.0 inbox, no env override):
   - `VENDOR=Microsoft Corporation / RENDERER=D3D12 (Qualcomm(R) Adreno(TM) 680 GPU) / VERSION=4.1 (Compatibility Profile) Mesa 26.3.0 / GLSL=4.10`
   - Not 4.2. The earlier "inbox=4.2" came from mmozeiko issue #22 on a different GPU. On this driver+inbox runtime it is **4.1**, which explains `GL_INVALID_ENUM` on `GL_MAX_IMAGE_UNITS` (4.2+ query). That error is non-fatal; stock closed on Blender's own gate, not on it.
   - Extensions (274 inbox): HAS `ARB_clip_control`, `ARB_shader_draw_parameters`, `ARB_shader_storage_buffer_object`, `ARB_multi_draw_indirect`, `ARB_base_instance`, `ARB_clear_texture`, `ARB_copy_image`, `ARB_draw_indirect`, tessellation, anisotropic. MISSING: `ARB_compute_shader` (0 hits), `ARB_shader_image_load_store` (0 hits). Full list: `logs/phase1/d3d12_exts_inbox.txt`.

3. D3D12 caps (dxdiag, device-measured): `DDI 12`, `WDDM 2.7`, **Feature Levels `12_1,12_0,11_1,11_0,...` (max 12_1, no 12_2)**, `Driver 27.20.2140.0`. `TypedUAVLoadAdditionalFormats` + shader model NOT yet measured: `D3D12CreateDevice`/`D3D12GetInterface` probes return `E_NOINTERFACE` from both ARM64 (Blender python) and emulated processes, and `D3D12GetInterface(CLSID_SDKConfiguration)` is absent on this inbox runtime — so the `SetSDKVersion`-without-exports route is closed. Remaining route is exe exports (Blender patch), which also unlocks the Agility GL-version test.

4. Agility cheapest experiment: **blocked without a Blender patch**. `D3D12GetInterface hr=0x80004002`, same GL 4.1 with/without attempt. Per MS docs the app-local runtime requires `D3D12SDKVersion`+`D3D12SDKPath` exported from the main exe (or `SetSDKVersion`, which this inbox lacks). Next step is a 2-export Blender test build + `D3D12/` dir, then re-run WGL probe with no override. No Mesa code until that number exists.

5. Gate: Gen2-lift+Mesa+override stays up 18s with `Limited Platform Support`, but **no screenshot of default cube/Solid orbit exists**. Treat as "dialog survived", not "viewport works". Owner to provide screenshot.
