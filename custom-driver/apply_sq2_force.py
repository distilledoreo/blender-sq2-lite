"""Apply the SQ2 force-on experiment to Mesa d3d12_screen.cpp.

Why python instead of `git apply` for this change: the two edits sit
directly on top of the probe patch's added lines, and `git apply`
refused to match that 4-line pre-image even though it is byte-identical
in the file (verified locally against Mesa 26.3.0; GNU patch accepts the
same hunk). A plain string replacement with an exact-count assertion is
deterministic and fails loudly on any mismatch.

Requires the probe patch already applied (CI applies probe for inputs
probe|force|both). With D3D12_SQ2_FORCE_IMAGES unset the built driver
behaves exactly like probe-only: the real flag is checked, the real
table is printed, the real result is returned.

Usage: python apply_sq2_force.py C:/m/src/gallium/drivers/d3d12/d3d12_screen.cpp
"""
import sys

PATH = sys.argv[1]
src = open(PATH, "r", newline="").read()
# CI checks out CRLF (runner default) regardless of clone flags; git apply
# tolerates that, plain string matching does not. Normalize to LF for
# matching; output stays LF, which MSVC and ninja accept. (Proven: a CRLF
# copy reproduces CI's `site 1: found 0` byte-for-byte.)
print(f"line endings: CRLF={src.count(chr(13))} lines")
src = src.replace("\r\n", "\n")

OLD1 = """   if (!screen->opts.TypedUAVLoadAdditionalFormats)
      return false;
"""
NEW1 = """   if (!screen->opts.TypedUAVLoadAdditionalFormats)
   {
      if (!os_get_option("D3D12_SQ2_FORCE_IMAGES"))
         return false;
      fprintf(stderr, "D3D12 SQ2: TypedUAV flag false, forcing past it (experimental)\\n");
   }
"""

OLD2 = """      if (!tuav || !load || !store)
         return false;
"""
NEW2 = """      if (!tuav || !load || !store) {
         if (!os_get_option("D3D12_SQ2_FORCE_IMAGES"))
            return false;
         fprintf(stderr, "D3D12 SQ2: forcing past failed format (experimental)\\n");
      }
"""

for i, (old, new) in enumerate(((OLD1, NEW1), (OLD2, NEW2)), 1):
    n = src.count(old)
    print(f"site {i}: found {n} occurrence(s)")
    if n != 1:
        anchor = old.strip().splitlines()[0]
        print(f"anchor line occurs {src.count(anchor)} time(s)")
        j = src.find(anchor)
        print("context: " + (repr(src[max(0, j-120):j+200]) if j >= 0 else "anchor absent"))
        raise SystemExit(f"expected exactly 1 match for site {i}, found {n}")
    src = src.replace(old, new)

open(PATH, "w", newline="").write(src)
print("force-on applied")
