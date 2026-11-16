# version.c 4.2 / 4.3 walk vs measured core list (195 exts)

Source for terms: `compute_version` in `src/mesa/main/version.c`
(read from mirror/mesa main; the 4.2/4.3 term lists are long-stable and
sit at the 26.3.0 line refs already recorded in GATES_VERIFIED.md).
Measured list: `logs/phase1/d3d12_exts_core41_unpatched.txt`
(core 4.1, inbox D3D12 runtime, Mesa 26.3.0 d3d12). Verdicts below were
machine-checked with grep, not eyeballed.

Accepted corrections to the earlier summary:
1. The 21-format gate result is UNMEASURED until the probe build runs.
   It is also two separate things: the 21-format capability gate
   (`can_shader_image_load_all_formats`) vs the `image_format_conversion`
   lowering table (only matters after the gate passes).
2. Force-on tests compute dispatch + SSBOs only (Solid path uses zero
   images). It says nothing about typed-UAV loads. A clean Solid result
   must not be read as EEVEE evidence.
3. "No override needed" is a prediction, and the walk below weakens it:
   4.3 has a failing term outside the images family.
4. Wording: Mesa 26.3.0 on the inbox D3D12 runtime, not "inbox Mesa".

## GL 4.2 (needs ver_4_1 = current 4.1, plus:)

| Term | Verdict |
|---|---|
| GLSLVersion >= 420 | reads 410 (see clamp note) |
| ARB_base_instance | PASS |
| ARB_conservative_depth | PASS |
| ARB_internalformat_query | PASS |
| ARB_shader_atomic_counters | PASS |
| ARB_shader_image_load_store | FAIL — images gate |
| ARB_shading_language_420pack | PASS |
| ARB_shading_language_packing | PASS |
| ARB_texture_compression_bptc | PASS |
| ARB_transform_feedback_instanced | PASS |

8/9 pass. Only the images gate fails.

## GL 4.3 (needs ver_4_2, plus:)

| Term | Verdict |
|---|---|
| GLSLVersion >= 430 | reads 410 (see clamp note) |
| Vertex MaxUniformBlocks >= 14 | unmeasured const; expected pass (UBO ext present, d3d12 exposes 14+) |
| ARB_ES3_compatibility | PASS |
| ARB_arrays_of_arrays | PASS |
| ARB_compute_shader | FAIL — depends on images (st gate) |
| ARB_copy_image | PASS |
| ARB_explicit_uniform_location | PASS |
| ARB_fragment_layer_viewport | PASS |
| ARB_framebuffer_no_attachments | PASS |
| ARB_internalformat_query2 | PASS |
| ARB_robust_buffer_access_behavior | PASS |
| ARB_shader_image_size | FAIL — images family (same gate neighborhood as load_store) |
| ARB_shader_storage_buffer_object | PASS |
| ARB_stencil_texturing | PASS |
| ARB_texture_buffer_range | PASS |
| ARB_texture_query_levels | PASS |
| ARB_texture_view | FAIL — NOT images-related; gate mechanism unverified |

12/15 pass (plus 2 const terms).

## New finding: ARB_texture_view

Absent from the 195-ext core list. Nothing in the st image gate
controls it, so force-on is not predicted to flip it. Two outcomes
from the force-on build's extension string settle it empirically:
- texture_view appears → its gate was images-dependent after all.
- texture_view still absent → 4.3 stays out of reach even with
  images+compute; next target is its st gate, and Blender keeps the
  Gen2-lift + override path while that is worked.

Either way, the realistic force-on landing zone is **4.2**, not 4.3.
Blender 5.x requires 4.3, so the override question is not closed by
force-on alone.

## GLSL clamp note

Measured "GLSL 4.10" is the *clamped* result: `_mesa_compute_version`
sets `GLSLVersion = Version * 10` for Version >= 33. The driver's raw
GLSLVersion cap (from shader-model mapping) is unmeasured and expected
>= 430 via SM 6.x. The force-on build's GLSL string verifies this:
if the version lands 4.2, raw cap was >= 420 by construction.

## What the force-on build settles (in order)

1. Probe table: TypedUAV flag, SM level, per-format load/store.
2. `both` + var set: GL version string + GLSL string (tests the
   "override goes away" prediction; expect 4.2 per texture_view).
3. `both` + var set ext string: compute_shader present?
   shader_image_size present? texture_view present/absent?
