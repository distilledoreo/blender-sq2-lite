#!/usr/bin/env python3
"""Apply SQ2 Gen2 lift (GL + Vulkan, robust).

Patches (all single-token UNSUPPORTED->LIMITED, no brace changes):
- gl_backend.cc: epoxy>=43, Qualcomm ver0<30 block, SSBO<12 (generic fallback).
- vk_backend.cc: first UNSUPPORTED -> LIMITED (Vulkan 1.1 vs 1.3 gate).
Never fails build (exits 0).
Usage: python apply_sq2_patches.py C:\\b
"""
import sys, re
from pathlib import Path

FENCE = (
    "\n    /* SQ2 Gen2 lift: Workbench-safe. Caps untouched for 5.2 API compat. */\n"
    "    /* SQ2_EEVEE_RASTER runtime flag handled by dxil_rewrite. */\n"
)

def flip_next_unsupported(text: str, marker: str, window: int = 2000):
    idx = text.find(marker)
    if idx < 0:
        # try without spaces
        idx = text.find(marker.replace(" ", ""))
        if idx < 0:
            return text, False
    tail = text[idx:idx + window]
    tail2 = tail.replace("GPU_SUPPORT_LEVEL_UNSUPPORTED", "GPU_SUPPORT_LEVEL_LIMITED /* SQ2 Gen2 */", 1)
    if tail2 == tail:
        return text, False
    return text[:idx] + tail2 + text[idx + window:], True

def patch_file(path: Path, markers):
    stats = {}
    if not path.exists():
        print(f"[SQ2] MISSING {path}")
        return stats
    t = path.read_text(encoding="utf-8", errors="ignore")
    orig = t
    # Fence: insert after opening brace of first marker block (if found).
    for m in markers:
        idx = t.find(m)
        if idx < 0:
            idx = t.find(m.replace(" ", ""))
        if idx >= 0:
            brace = t.find("{", idx)
            if 0 < brace - idx < 800:
                t = t[:brace + 1] + FENCE + t[brace + 1:]
                print(f"[SQ2] fenced {path.name} after '{m}'")
                break
    # Flip next UNSUPPORTED after each marker.
    for m in markers:
        t, ok = flip_next_unsupported(t, m)
        stats[m] = ok
        print(f"[SQ2] {'patched' if ok else 'MISS'} {path.name} :: {m}")
    if t != orig:
        path.write_text(t, encoding="utf-8")
        print(f"[SQ2] wrote {path}")
    return stats

def main():
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("C:/b")
    print(f"[SQ2] applying Gen2 lift in {root}")
    gl = root / "source" / "blender" / "gpu" / "opengl" / "gl_backend.cc"
    vk = root / "source" / "blender" / "gpu" / "vulkan" / "vk_backend.cc"
    s1 = patch_file(gl, ["epoxy_gl_version() >= 43", "ver0 < 30", "max_ssbo_binds"])
    # SSBO generic: if max_ssbo_binds marker missed, flip any SSBO-related UNSUPPORTED
    # (already covered by marker search above).
    s2 = patch_file(vk, ["VK_API_VERSION_1_3", "dynamic_rendering", "timelineSemaphore", "VK_KHR_dynamic_rendering"])
    # Vulkan fallback: if none matched (names shift), flip first UNSUPPORTED in file to LIMITED.
    if not any(s2.values()):
        t = vk.read_text(encoding="utf-8", errors="ignore") if vk.exists() else ""
        if "GPU_SUPPORT_LEVEL_UNSUPPORTED" in t:
            t = t.replace("GPU_SUPPORT_LEVEL_UNSUPPORTED", "GPU_SUPPORT_LEVEL_LIMITED /* SQ2 Gen2 vulkan */", 1)
            vk.write_text(t, encoding="utf-8")
            print("[SQ2] Vulkan fallback: flipped first UNSUPPORTED -> LIMITED")
            s2["fallback"] = True
    print(f"[SQ2] done gl={s1} vk={s2}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
