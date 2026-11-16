# Phase 2 cap map (Mesa d3d12 26.3.0 on SQ2, device-measured)

Source: Mesa main `src/gallium/drivers/d3d12/d3d12_screen.cpp` (68KB, fetched 2026-11-16) + WGL probes.

## GL version truth
- Inbox AND Agility-619 (exe exports): `4.1 Compatibility, GLSL 4.10`, 274 exts. Docs say d3d12 targets 3.3 conformance; 4.1 here is already above that.
- Env route exists in source: `D3D12_AGILITY_RELATIVE_PATH` + `D3D12_AGILITY_SDK_VERSION` -> `sdk_config->SetSDKVersion()`. Tested: same 4.1. Agility changes runtime, not Qualcomm caps (FL max 12_1, driver 27.x).

## The two gaps
1. Images: `screen->support_shader_images = can_shader_image_load_all_formats()` requires `opts.TypedUAVLoadAdditionalFormats` AND 21 extra DXGI formats with `UAV_TYPED_LOAD|STORE` (R16G16B16A16_UNORM/SNORM, R32G32_*, R10G10B10A2_*, R11G11B10F, R8G8B8A8_SNORM, R16G16_*, R8G8_*, R16_*, R8_SNORM). False on this driver -> `max_shader_images=0` -> no `ARB_shader_image_load_store` (0 hits). This is the `GL_MAX_IMAGE_UNITS` error: 4.1 has no images.
2. Compute: `d3d12_init_compute_caps` sets grid/block caps and `caps->compute=true`, but GL `ARB_compute_shader` needs the compute *shader stage* path; 0 hits in ext list. `D3D12_DEBUG=experimental` (experimental shader models) kills context creation entirely on this driver. So compute is unavailable, not just hidden.

## What this means for Blender
- Present (good for new draw manager): SSBO, multi_draw_indirect, draw_parameters, clip_control, base_instance, clear_texture, copy_image, tessellation, anisotropic.
- Missing: compute (culling/gsplats) + images. Draw-manager docs list Compute Visibility + Generate Commands; 2023 notes confirm compute-based culling. GPU-module docs: compute must be gated by `GPU_compute_shader_support()` with CPU fallback. So Solid *may* still draw via fallback — unproven without screenshot.
- Fencing EEVEE is not sufficient: the question is the Solid viewport, and its culling path wants compute.

## No Mesa fork until screenshot
Next: owner screenshot of default cube in Solid + orbit on Gen2-lift+Mesa+override. If Solid draws (even slow), keep gate patches only. If it fails on compute/image shader compile, that log line defines the Mesa work — likely TypedUAV format lowering + SM-gated compute, both in `d3d12_*`, not a DXIL rewriter.
