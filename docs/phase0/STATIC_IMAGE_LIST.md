# Static image list v2 (2026-11-16, corrected + controlled)

Source: Blender main, sparse checkout `source/blender/draw` + `source/blender/gpu`.

## Control (patterns valid)
Same patterns on `draw/engines/eevee`: **446 hits** (`[[image(slot, qual, FORMAT)]]`, `imageStore`/`imageLoad`). BSL syntax confirmed.

## Solid path: zero images for the default cube
- `[[image(` / `imageStore` / `imageLoad` / `imageAtomic` in ALL `.bsl.hh` under `draw/intern/shaders`, `draw/engines/{workbench,overlay,select}`: **0 hits**.
- `gpu/shaders` + `gpencil` + `image` engine hits are CPU-side compat shims (`gpu_shader_cxx_image.hh` host stubs), except gpencil below.
- Workbench "image" files use `[[sampler]] sampler2D` texture sampling only.

## Exceptions (not hit by default-cube Solid, matter later)
- **Grease pencil** (`gpencil_antialiasing`, `gpencil_depth_merge`): 3 image decls — `SFLOAT_16_16_16_16` read + read_write, `SFLOAT_32` read_write. Only compiles with GP objects present.
- **EEVEE** (Material Preview thumbnails, Material Preview, Rendered): heavy image use WITH reads, incl. the costly 64-bit case: `SFLOAT_16_16_16_16` read + read_write (radiance_feedback, inout_color, out_combined, color_accum, in_normal...), `SFLOAT_16` read/write, `SFLOAT_32`/`SINT_32`/`UINT_32`, `SFLOAT_32_32_32_32` (128-bit), `UNORM_16_16`, `UFLOAT_11_11_10`, `RAYTRACE_RADIANCE_FORMAT`. Keep EEVEE fenced while the gate is forced: Mesa will claim formats the driver cannot load.

## Corrections accepted
- Version number matters: Blender requests 4.3 core + checks at startup (override still needed until Mesa reports 4.3).
- GLSL 4.10 is the compat-context result (`version.c:581` clamps desktop GLSL to compat in compat profiles; d3d12 driver reports 460, used on core paths). Force-on lifts version + GLSL together or stops at the next `version.c` term — record which.
