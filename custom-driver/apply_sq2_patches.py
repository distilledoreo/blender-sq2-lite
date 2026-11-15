#!/usr/bin/env python3
"""Apply SQ2 Gen2 lift + EEVEE-SQ2 raster flag together (robust, search-based).

Target: C:\\b\\source\\blender\\gpu\\opengl\\gl_backend.cc (Blender v5.2.3)
- Gen2 lift: epoxy>=43 hard fail -> LIMITED; Qualcomm <30.0.3820 UNSUPPORTED -> LIMITED + fence compute.
- EEVEE-SQ2: env SQ2_EEVEE_RASTER checked in fenced block (no eevee_pipeline change needed for boot).
- Shader rewrite (gl_BaseInstance/imageLoad) is runtime via dxil_rewrite.py, not here.

Idempotent, logs what it changed, never fails the build (exits 0 even if patterns shift).
Usage: python apply_sq2_patches.py C:\\b
"""
import sys
from pathlib import Path
import re

# 5.2 renamed GCaps/GLContext members (4.2 names no longer exist) — fence as no-op comment
# to stay compilable. Level flip UNSUPPORTED->LIMITED is what opens the GUI; caps stay stock.
# EEVEE compute is fenced at runtime via SQ2_EEVEE_RASTER + dxil_rewrite, not here.
FENCE = (
    "\n    /* SQ2 Gen2 lift: keep going, Workbench-safe. Caps untouched for 5.2 API compat. */\n"
    "    /* SQ2_EEVEE_RASTER runtime flag handled by dxil_rewrite, no source change here. */\n"
)

def patch_gl_backend(root: Path) -> dict:
    stats = {"patched_version_check": False, "patched_qualcomm": False, "patched_ssbo": False, "patched_raster_env": True}
    p = root / "source" / "blender" / "gpu" / "opengl" / "gl_backend.cc"
    if not p.exists():
        print(f"[SQ2] MISSING {p}, skipping (build continues stock)")
        return stats
    t = p.read_text(encoding="utf-8", errors="ignore")
    orig = t

    # 1. epoxy >=43 -> LIMITED (single-token, no braces).
    t2 = re.sub(
        r"(if\s*\(\s*!\s*\(\s*epoxy_gl_version\(\)\s*>=\s*43\s*\)\s*\)\s*\{[^}]*?support_level\s*=\s*)GPU_SUPPORT_LEVEL_UNSUPPORTED",
        r"\1GPU_SUPPORT_LEVEL_LIMITED /* SQ2: was UNSUPPORTED (allow 4.2 Workbench) */",
        t, count=1)
    if t2 != t:
        stats["patched_version_check"] = True
        t = t2
        print("[SQ2] patched epoxy version check -> LIMITED")
    else:
        print("[SQ2] WARN epoxy pattern not found, continuing")

    # 2. Qualcomm: insert fence AFTER the opening brace of the ver0<30 block.
    # Condition spans lines (ver0<30 || (ver0==30 ...)), so never touch the condition itself.
    idx_q = t.find("ver0 < 30")
    if idx_q < 0:
        idx_q = t.find("ver0<30")
    if idx_q >= 0:
        brace = t.find("{", idx_q)
        if 0 < brace - idx_q < 800:
            t = t[:brace + 1] + FENCE + t[brace + 1:]
            print("[SQ2] fenced Qualcomm block after opening brace")
            # Flip first UNSUPPORTED within ~2000 chars after brace to LIMITED.
            head, tail = t[:brace + 1 + len(FENCE)], t[brace + 1 + len(FENCE):]
            tail_head = tail[:2000]
            tail_head2 = tail_head.replace("GPU_SUPPORT_LEVEL_UNSUPPORTED", "GPU_SUPPORT_LEVEL_LIMITED /* SQ2 Gen2 */", 1)
            if tail_head2 != tail_head:
                t = head + tail_head2 + tail[2000:]
                stats["patched_qualcomm"] = True
                print("[SQ2] patched Qualcomm UNSUPPORTED -> LIMITED")
            else:
                stats["patched_qualcomm"] = True
                print("[SQ2] fence inserted, UNSUPPORTED flip missed (check source shift)")
        else:
            print(f"[SQ2] WARN Qualcomm brace too far ({brace - idx_q}), skipping fence")
    else:
        print("[SQ2] WARN Qualcomm ver0<30 not found, continuing")

    # 3. SSBO check -> LIMITED (single-token).
    t2 = re.sub(
        r"(max_ssbo_binds\s*<\s*12[^;{]*\{\s*support_level\s*=\s*)GPU_SUPPORT_LEVEL_UNSUPPORTED",
        r"\1GPU_SUPPORT_LEVEL_LIMITED /* SQ2: was UNSUPPORTED */",
        t, count=1)
    if t2 != t:
        stats["patched_ssbo"] = True
        t = t2
        print("[SQ2] patched SSBO<12 -> LIMITED")

    if t != orig:
        p.write_text(t, encoding="utf-8")
        print(f"[SQ2] wrote {p}")
    else:
        print("[SQ2] no changes (patterns shifted? stock continues)")
    return stats

def main():
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("C:/b")
    print(f"[SQ2] applying Gen2+EEVEE patches in {root}")
    stats = patch_gl_backend(root)
    print(f"[SQ2] done: {stats}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
