# Console finding (2026-11-16): draw_resource_finalize "no shaders attached"

## Log (Gen2-lift + Mesa d3d12 + 4.3 override, exit 11)
- `00:07.407 gpu.shader ERROR draw_resource_finalize Linking: Error: no shaders attached to the program` then `Writing blender.crash.txt`.
- No `CompShader` error above it: the compute stage was never compiled — creation skipped, link of empty program failed, `StaticShader.get()` null, `Manager::end_sync` (`draw_manager.cc:134-140`: bind + 3 SSBO binds + `GPU_compute_dispatch`) crashed on bind.
- Full: `logs/phase1/console_draw_resource_finalize_fail.txt`. First crash: `logs/phase1/console_first_crash_out.txt`.

## Verified in source (v5.2.3)
- `Manager::end_sync` always dispatches `DRW_shader_draw_resource_finalize_get()` compute with `matrix_buf/bounds_buf/infos_buf` SSBOs before any engine draws. Not engine-specific; fencing EEVEE/Workbench cannot avoid it. Will not patch a skip (output required downstream).

## dxil.dll: checked, not the fix for exposure
- ARM64 `dxil.dll` (3.3MB, Edge WebView 26100) placed beside exe. Ext list unchanged (274, no compute/image), same link error. Mesa 26.3 graphics shaders compile without it; compute creation is skipped earlier (capability gate, not signing). Left in place — will be needed for signing once compute is exposed.

## Agility state
- Crash modules: inbox `D3D12Core 10.0.26100.9818` (this Blender has no SDK exports — expected). Probe-exe test proved exports+619 still report 4.1 on this driver, so a Blender+Agility rebuild is not the next step for GL version.

## Fills user's table
- True caps no override: 4.1 compat / GLSL 4.10, SSBO yes, compute no, images no (`logs/phase1/d3d12_exts_inbox.txt`).
- With Agility: same 4.1, same set (`logs/phase1/agility_619_nooverride.txt` + env variant).
- Remaining baseline gap: numeric SM + TypedUAVLoadAdditionalFormats (COM probes return E_NOINTERFACE on this box). Functional proof stands in: `support_shader_images=false` (no image ext, GL_MAX_IMAGE_UNITS error) and compute stage absent.
- Row hit: **compute still missing** → Phase 2 = find the D3D12 cap gating compute in `d3d12_screen` (SM-gated path; `D3D12_DEBUG=experimental` kills context creation on 27.x, so not a toggle fix).
