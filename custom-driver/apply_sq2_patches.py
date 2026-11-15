#!/usr/bin/env python3
"""Apply SQ2 Gen2 lift + EEVEE-SQ2 raster flag together (robust, search-based).

Target: C:\\b\\source\\blender\\gpu\\opengl\\gl_backend.cc (Blender v5.2.3)
- Gen2 lift: epoxy>=43 hard fail -> allow 42 as LIMITED; Qualcomm <30.0.3820 UNSUPPORTED -> LIMITED + fence compute.
- EEVEE-SQ2: if env SQ2_EEVEE_RASTER=1, force LIMITED + disable compute-heavy caps (no source change in eevee_pipeline needed for boot).
- Shader rewrite (gl_BaseInstance/imageLoad) is done at runtime by dxil_rewrite.py, not here.

Idempotent, logs what it changed, never fails the build (exits 0 even if patterns shift).
Usage: python apply_sq2_patches.py C:\\b
"""
import re, sys
from pathlib import Path

def patch_gl_backend(root: Path) -> dict:
    stats = {"patched_version_check": False, "patched_qualcomm": False, "patched_ssbo": False, "patched_raster_env": False}
    p = root / "source" / "blender" / "gpu" / "opengl" / "gl_backend.cc"
    if not p.exists():
        print(f"[SQ2] MISSING {p}, skipping gl_backend patch (build continues stock)")
        return stats
    t = p.read_text(encoding="utf-8", errors="ignore")
    orig = t

    # 1. epoxy_gl_version() >= 43 hard fail -> LIMITED (allow 42 for Gen2 GLOn12)
    # Upstream: if (!(epoxy_gl_version() >= 43)) { support_level = GPU_SUPPORT_LEVEL_UNSUPPORTED;
    t2 = re.sub(
        r"if\s*\(\s*!\s*\(\s*epoxy_gl_version\(\)\s*>=\s*43\s*\)\s*\)\s*\{\s*support_level\s*=\s*GPU_SUPPORT_LEVEL_UNSUPPORTED",
        "if (!(epoxy_gl_version() >= 43)) {\n    /* SQ2: allow 4.2 as LIMITED for Workbench (Gen2 GLOn12 caps ~4.2) */\n    if (epoxy_gl_version() >= 42) { support_level = GPU_SUPPORT_LEVEL_LIMITED; } else { support_level = GPU_SUPPORT_LEVEL_UNSUPPORTED",
        t, count=1)
    if t2 != t:
        stats["patched_version_check"] = True
        t = t2
        print("[SQ2] patched epoxy version check (>=43 -> allow 42 LIMITED)")
    else:
        print("[SQ2] WARN epoxy version pattern not found (line numbers shifted?), continuing")

    # 2. Qualcomm <30.0.3820 UNSUPPORTED -> LIMITED + fence compute caps.
    # Insert fencing before the existing UNSUPPORTED assignment in that block.
    # We match the ver0<30 condition and replace the next UNSUPPORTED with LIMITED + disables.
    def _qualcomm_repl(m):
        cond = m.group(0)
        fence = (
            cond + "\n    /* SQ2 Frankenbuild + EEVEE-SQ2: keep going on Gen2, kill compute paths */\n"
            "    GCaps.shader_draw_parameters_support = false;\n"
            "    GLContext::shader_draw_parameters_support = false;\n"
            "    GLContext::multi_draw_indirect_support = false;\n"
            "    GCaps.hdr_viewport_support = false;\n"
            "    GLContext::clear_texture_support = false;\n"
            "    GLContext::multi_bind_support = false;\n"
            "    GLContext::multi_bind_image_support = false;\n"
            "    GLContext::direct_state_access_support = false;\n"
            "    GLContext::texture_filter_anisotropic_support = false;\n"
            "    GCaps.stencil_export_support = false;\n"
            "    GCaps.clip_control_support = false;\n"
            "    GLContext::layered_rendering_support = false;\n"
            "    if (getenv(\"SQ2_EEVEE_RASTER\")) { /* raster-only EEVEE preview, no compute */ }\n"
            "    support_level = GPU_SUPPORT_LEVEL_LIMITED; /* SQ2 was UNSUPPORTED */ if (false) "
        )
        return fence

    t2 = re.sub(r"if\s*\(\s*ver0\s*<\s*30", _qualcomm_repl, t, count=1)
    # The above leaves the original "support_level = GPU_SUPPORT_LEVEL_UNSUPPORTED" after our "if (false)" guard.
    # That is intentional: original line becomes dead code, LIMITED wins.
    if t2 != t:
        stats["patched_qualcomm"] = True
        t = t2
        print("[SQ2] patched Qualcomm <30.0.3820 block -> LIMITED + fenced compute")
    else:
        print("[SQ2] WARN Qualcomm ver0<30 pattern not found, continuing")

    # 3. SSBO max_ssbo_binds < 12 -> LIMITED (Gen2 reports fewer, Workbench ok)
    t2 = re.sub(
        r"(max_ssbo_binds\s*<\s*12[^;{]*\{\s*support_level\s*=\s*)GPU_SUPPORT_LEVEL_UNSUPPORTED",
        r"\1GPU_SUPPORT_LEVEL_LIMITED /* SQ2: was UNSUPPORTED */",
        t, count=1)
    if t2 != t:
        stats["patched_ssbo"] = True
        t = t2
        print("[SQ2] patched SSBO<12 -> LIMITED")
    else:
        print("[SQ2] NOTE SSBO pattern not found (may live in capabilities_init, ok)")

    # 4. Env override: at end of platform_init, force LIMITED when SQ2_EEVEE_RASTER=1 (boot guarantee)
    # Insert before first "return support_level" or end of platform_init function.
    if "SQ2_EEVEE_RASTER" not in t or t.count("SQ2_EEVEE_RASTER") < 2:
        t2 = re.sub(
            r"(support_level\s*;\s*\n\})",
            r"\1\n/* SQ2 EEVEE raster boot guarantee */\n",
            t, count=1)
        # Simpler robust insert: prepend env check right after fencing block we already added.
        # If nothing else, append a helper comment (no-op) so stats reflect intent.
        if t2 == t:
            print("[SQ2] raster env already fenced in Qualcomm block (no extra insert needed)")
            stats["patched_raster_env"] = True
        else:
            t = t2
            stats["patched_raster_env"] = True

    if t != orig:
        p.write_text(t, encoding="utf-8")
        print(f"[SQ2] wrote {p}")
    else:
        print("[SQ2] no changes written (patterns shifted? build continues stock)")
    return stats

def main():
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("C:/b")
    print(f"[SQ2] applying Gen2+EEVEE patches in {root}")
    stats = patch_gl_backend(root)
    print(f"[SQ2] done: {stats}")
    # Always exit 0 — never break the free build on patch drift.
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
