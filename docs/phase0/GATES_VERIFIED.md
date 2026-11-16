# Gate conditions, verified in source (2026-11-16)

You were right: single root cause (images), not SM-gated compute. Withdrawing "SM-gated".

## Gate 1 — st/mesa (`src/mesa/state_tracker/st_extensions.c`)
```
extensions->ARB_compute_shader =
   screen->compute_caps.max_threads_per_block >= 1024 &&   // d3d12 sets 1024 (D3D12_CS_THREAD_GROUP_MAX_THREADS_PER_GROUP) -> PASS
   extensions->ARB_shader_image_load_store &&              // FAIL (below) -> whole thing false
   extensions->ARB_shader_atomic_counters;                 // PASS via SSBO fallback (st:299-308 reserves half SSBOs; SSBO ext present on device)
```
Corroborating gates: `ARB_ES3_1_compatibility` also requires compute+images+SSBO+draw_indirect (st:1798-1812); GL 4.2 needs images. One missing capability explains 4.1 + no compute together. Matches other GLOn12-on-Intel 4.1 reports.

## Gate 2 — Mesa d3d12 (`src/gallium/drivers/d3d12/d3d12_screen.cpp`)
```
screen->support_shader_images = can_shader_image_load_all_formats(screen);   // line 1825
  -> false unless opts.TypedUAVLoadAdditionalFormats
  -> AND 21 DXGI formats each satisfy: CheckFeatureSupport(FORMAT_SUPPORT) ok,
     Support1 has TYPED_UNORDERED_ACCESS_VIEW,
     Support2 has (UAV_TYPED_LOAD | UAV_TYPED_STORE):
     R16G16B16A16_UNORM/SNORM, R32G32_FLOAT/UINT/SINT, R10G10B10A2_UNORM/UINT,
     R11G11B10_FLOAT, R8G8B8A8_SNORM, R16G16_FLOAT/UNORM/UINT/SNORM/SINT,
     R8G8_UNORM/UINT/SNORM/SINT, R16_UNORM/SNORM, R8_SNORM
```
`support_shader_images=false` -> `max_shader_images=0` (init_shader_caps:190 skips) -> `MaxImageUniforms=0` -> `ARB_shader_image_load_store=false` (st:584 needs fragment MaxImageUniforms + `image_store_formatted`, which d3d12 sets true at line 347).
`can_attribute_at_vertex` vendor special-case (MICROSOFT=true) is unrelated.
Agility env route confirmed in source: `D3D12_AGILITY_RELATIVE_PATH` + `D3D12_AGILITY_SDK_VERSION` -> `sdk_config->SetSDKVersion()` (lines 1546-1550). Tested: same 4.1.

## Probe status (honest limitation)
`D3D12CreateDevice` returns `E_NOINTERFACE` for NULL adapter AND explicit DXGI adapter0, ARM64-native and emulated, FL 11_0 and 12_1; `D3D12GetInterface(CLSID_SDKConfiguration)` with standard GUIDs also `E_NOINTERFACE`. Mesa itself succeeds via the `ID3D12DeviceFactory` path (line 1557). Numeric SM + TypedUAV flag + per-format table still unmeasured directly; functional proof stands in (no image ext, `GL_MAX_IMAGE_UNITS` error, "no shaders attached" link error).

## Phase 2 scope (small, per your table)
1. Mesa-fork experiment: force `support_shader_images=true` (or stub the 21-format check to the 3 always-working formats R32F/UINT/SINT), build, launch no-override. `draw_resource_finalize` uses only SSBOs (draw_manager.cc:134-140) so it may compile with zero image support.
2. Record: GL version, finalize compile, then which shaders fail on image loads + formats.
3. Lowering only for formats in that list, honoring: loads-only limit, no FLOAT<->non-FLOAT casts, 32-bit texels via R32_UINT unpack, RGBA16F-class needs real support (reassess if hit).
