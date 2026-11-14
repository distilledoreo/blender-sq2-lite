# Unclosing EEVEE on SQ2 — full-speed plan (no CPU fallback)

You said think bigger. OK. Stop trying to fix the kernel. Fix the shaders.

## Why EEVEE is "closed" (exactly 3 locks, not 100)

From Blender source + Qualcomm notes, EEVEE-Next on Windows dies on Gen2 for:

1. `D3D typed UAV load` missing in KMD <30.0.3820 → all OpenGL compute / Vulkan storage-image typed loads fail.
2. `GL_ARB_shader_draw_parameters / gl_BaseInstance` missing → EEVEE indirect draws fail.
3. `VK_KHR_dynamic_rendering + timelineSemaphore` missing (Vulkan 1.1 only) → EEVEE-Vulkan backend refuses to start.

WARP/CPU "fixes" all three by doing everything on CPU. Too slow. Rejected.

## Unclose: keep everything on Adreno, rewrite around the 3 locks

Adreno 690 CAN do: vertex/pixel shaders, raster, D3D11 Compute CS 5.0, structured buffers, R32F texture fetch via pixel path.
It CAN'T do (via this KMD): typed image load in compute stage.

So we don't emulate on CPU. We recompile EEVEE shaders to phrasing the hardware already understands:

- Typed `imageLoad(rgba32f)` → structured `ByteAddressBuffer.Load()` + `asfloat()` bit-cast. Same bytes, same GPU, different opcode. Full speed.
- `gl_BaseInstance` → push-constant `sq2_baseInstance`. EEVEE indirect draws become direct draws with uniform. Full speed.
- `dynamicRendering` → classic `vkBeginRenderPass`. Dynamic rendering is sugar. Mesa already has this fallback internally. Full speed.
- `timelineSemaphore` → binary semaphore + fence chain. Slight CPU sync cost, not pixels. ~2% hit.

None of this needs Qualcomm signing. It lives in two places you own:
`dxil_rewrite.py` (app-local D3D12/DXIL hook) + `blender_eevee_sq2_fallback.patch` (Blender source, EEVEE-SQ2 raster path).

This is how console emulators unclose GPUs: not new silicon, new wording.

See other files in this folder for starters.
