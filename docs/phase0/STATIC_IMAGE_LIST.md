# Static image list: Solid-mode path uses ZERO images (2026-11-16)

Source: Blender main, sparse checkout `source/blender/draw` + `source/blender/gpu` (`/c/blender-src-stat`).

## Method
- `IMAGE(` macro users in draw+gpu: only `gpu_shader_test_infos.hh` (tests) + `vk_backbuffer_blit_infos.hh` (Vulkan-only blit).
- `[[image` / `image2D` / `imageStore` / `imageLoad` / `imageAtomic` in ALL `.bsl.hh` under `draw/intern/shaders`, `draw/engines/workbench`, `draw/engines/overlay`, `draw/engines/select`: **zero hits**.
- The 5 `image`-matching workbench files use `[[sampler...]] sampler2D` texture sampling only.

## Solid path compute shaders (all SSBO-only)
| Shader | Resources |
|---|---|
| draw_resource_finalize | 3 SSBO (matrix read, bounds/infos read_write) + push const |
| draw_visibility | SSBO bounds read, visibility read_write |
| draw_command_generate | SSBO group rw, visibility/prototype read, command + resource_id write |
| draw_view_finalize | (same pattern, SSBO) |
| workbench_shadow_visibility | SSBO bounds read, visibility bufs read_write |

## Consequence for the force-on experiment
- `draw_resource_finalize` needs no image support, so it should compile once compute exists.
- No Solid shader reads images => forcing `support_shader_images=true` risks no wrong pixels on this path. Watch overlays (wireframe/outline use samplers, verified) and report any shader that fails on image loads with its format.
- Version caveat (`version.c:349-377`): 4.2 needs GLSL>=420 + images + atomics + others; 4.3 needs compute + 14 UBOs + more. Current GLSL is 4.10, so the experiment may stop at 4.1/4.2 — record the reported version regardless; compute existing is the gating result, not the number.
