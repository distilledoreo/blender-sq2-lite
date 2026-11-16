"""Apply the end_batch entry print for the SQ2 instrument build.

Same story as apply_sq2_force.py: this 3-line context hunk is byte-identical
in the file, yet `git apply` (and GNU patch) refuse it while accepting every
other hunk in the same patch. A plain string replacement with an
exact-count assertion is deterministic and fails loudly on any mismatch.

Requires the git patch (H1-H7) already applied. CI applies it for
patches=instrument after the force applier.
CRLF-tolerant: CI checks out CRLF; normalize to LF for matching (MSVC and
ninja accept LF output).

Usage: python apply_sq2_instrument.py C:/m/src/gallium/drivers/d3d12/d3d12_batch.cpp
"""
import sys

PATH = sys.argv[1]
src = open(PATH, "r", newline="").read()
print(f"line endings: CRLF={src.count(chr(13))} lines")
src = src.replace("\r\n", "\n")

OLD = """d3d12_end_batch(struct d3d12_context *ctx, struct d3d12_batch *batch)
{
   struct d3d12_screen *screen = d3d12_screen(ctx->base.screen);
"""
NEW = """d3d12_end_batch(struct d3d12_context *ctx, struct d3d12_batch *batch)
{
   struct d3d12_screen *screen = d3d12_screen(ctx->base.screen);
   fprintf(stderr, "D3D12 SQ2: end_batch enter (experimental)\\n");
"""

n = src.count(OLD)
print(f"site: found {n} occurrence(s)")
if n != 1:
    raise SystemExit(f"expected exactly 1 match, found {n}")
src = src.replace(OLD, NEW)

open(PATH, "w", newline="").write(src)
print("instrument end_batch applied")
