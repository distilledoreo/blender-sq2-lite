## SQ2 Custom Driver — what "custom driver" can actually mean (no BS)

You said don't take no for an answer. Fair. Here's the honest split:

### What you CAN'T build (even with source + time)
A kernel-mode Adreno 690 Windows driver that adds typed-UAV / compute.

Why:
- Adreno firmware + KGSL/KMD interface on Windows is closed, Secure Boot + WHQL signing enforced.
- Qualcomm EOL'd 8cx Gen2 Windows graphics (27-28.x branch). No new KMD coming.
- Even Freedreno/Turnip (open Adreno 6xx driver, GL 4.5 / Vulkan 1.3, supports a690) needs Linux DRM/KGSL to submit work. On Windows there is no DRM to submit to — only Qualcomm's KMD, which hides the missing feature.
- You cannot create silicon features in software at hardware speed. Typed-UAV loads for EEVEE-Next compute need the D3D12 driver to expose them.

Anyone promising full-speed EEVEE-Next on SQ2 via a kernel driver is lying.

### What you CAN build (userspace, no signing, app-local)
A **Blender-folder-only OpenGL ICD/shim** that gives Workbench/Solid hardware speed on the D3D11 path that *does* work on Gen2 (browsers prove it: ANGLE→D3D11 is smooth).

Key insight from research today:
- Mesa `d3d12` Gallium driver on Windows only exposes **GL 3.3** (docs.mesa3d.org/drivers/d3d12.html) — not enough, Blender 5 needs 4.3.
- Mesa on Windows auto-builds: `llvmpipe, softpipe, zink, d3d12` — no `freedreno` on Windows (needs DRM).
- Freedreno GL 4.5 + Turnip Vulkan 1.3 *do* support Adreno 6xx including 690 — but only on Linux.
- Blender 5.2 hard needs: `GL 4.3 + GL_ARB_shader_draw_parameters + GL_ARB_clip_control`, Vulkan `1.3 + VK_KHR_dynamic_rendering`. Gen2 caps at ~GL 4.2 via GLOn12, Vulkan 1.1.

Good news: for **Solid/Wireframe only**, those two GL extensions ARE CPU-emulatable:
- `clip_control` = depth-range transform, can be patched into projection matrices.
- `shader_draw_parameters` (`gl_BaseInstance`, `gl_DrawID`) = can be replaced with a uniform + shader rewrite for the simple multi-draw Workbench uses.
- What CAN'T be emulated at speed: compute + SSBO-heavy EEVEE-Next. That's why EEVEE stays OFF in this plan — same rule as Frankenbuild.

So the custom driver is: **app-local `opengl32.dll` proxy + shader rewriter for Workbench, EEVEE fenced off.** No kernel, no signing, drop next to `blender.exe`.

See:
- `BUILD_MESA_SQ2.md` — how to build real Mesa 26.x for ARM64 Windows (d3d12+zink baseline to fork from)
- `shim/sq2_gl_shim.c` — starter proxy DLL: version lie + extension spoof + Workbench-only guard
- `shim/sq2_vk_layer.json` — Vulkan layer stub plan (spoof 1.3/dynamic-rendering check for Workbench, reject EEVEE)
