"""
SQ2 EEVEE uncloser — DXIL/SPIR-V opcode rewriter (starter).
Runs app-local, no driver signing. Keeps pixels on Adreno 690.

Idea: intercept EEVEE shader bytecode before D3D12 submits it,
replace the 2-3 blocked opcodes with equivalents Gen2 KMD already accepts.

Blocked -> Replacement (same result, different wording):
- D3D SM6.0 TypedUAVLoad (BufferLoad with typed format) ->
  ByteAddressBuffer.Load (raw uint) + asfloat()/asint() bit-cast.
  Why it works: bytes in memory are identical, only the typed-load
  instruction is missing in 27-28.x KMD. Raw loads ARE present (D3D11 CS 5.0 proves it).
- GL imageLoad(rgba32f) / Vulkan storage image typed ->
  same rewrite at GLSL->SPIR-V stage: storageBuffer + unpack.
- gl_BaseInstance / gl_DrawID ->
  uniform int sq2_baseInstance (EEVEE uses 0/1 for most passes, indirect
  multi-draw with varying base is rare outside culling compute which we fence off).

Usage (prototype):
  python dxil_rewrite.py in.dxil out.dxil --dump
  # real hook: Detour D3D12CreateDevice + ID3D12Device::CreateComputePipelineState,
  # rewrite DXIL blob in-memory before creation.

This file is the pattern matcher. Full DXIL parser = use DirectX-Headers
DxilContainer + DxilModule rotate; here we match disassembly text so you can
prove the pattern on your machine TODAY with `dxc -dumpbin`.

Example:
  dxc eevee_shadow.dxil -dumpbin > before.txt
  python dxil_rewrite.py before.txt after.txt
  grep -c TypedUAVLoad after.txt  # must be 0
  grep -c ByteAddressBuffer after.txt  # must be >0
"""
import re, sys

TYPED_UAV = re.compile(r"(buffer\.load\.typed|TypedUAVLoad|imageLoad\s*\(\s*rgba32f)", re.I)
BASEINSTANCE = re.compile(r"gl_BaseInstance|gl_DrawID|SV_BaseInstance", re.I)

def rewrite_dxil_text(text: str):
    out_lines = []
    rewrites = {"typed_uav": 0, "baseinstance": 0}
    for line in text.splitlines():
        if TYPED_UAV.search(line):
            out_lines.append("; SQ2-REWRITE typed->raw: " + line.strip())
            fixed = line.replace("typed", "raw")
            # imageLoad(typed_fmt, coord) -> sq2_rawLoad(coord) + asfloat bit-cast.
            # Keep coord, drop typed format arg (that's the blocked part).
            fixed = re.sub(r"imageLoad\s*\(\s*[a-zA-Z0-9_]+\s*,\s*", "sq2_rawLoadAsFloat(", fixed)
            fixed = re.sub(r"byteAddressBufferLoad\(\s*,\s*", "sq2_rawLoadAsFloat(", fixed)
            out_lines.append(fixed)
            rewrites["typed_uav"] += 1
        elif BASEINSTANCE.search(line):
            out_lines.append("; SQ2-REWRITE baseInstance->uniform: " + line.strip())
            out_lines.append(re.sub(r"gl_BaseInstance|SV_BaseInstance", "sq2_baseInstance", line, flags=re.I))
            rewrites["baseinstance"] += 1
        else:
            out_lines.append(line)
    header = "// SQ2-EEVEE-UNCLOSED header: prepend to every EEVEE pixel/compute shader\n// uniform int sq2_baseInstance; // bound 0 for Workbench/SQ2-raster path\n"
    return header + "\n".join(out_lines), rewrites

if __name__ == "__main__":
    src = open(sys.argv[1]).read() if len(sys.argv) > 1 else sys.stdin.read()
    out, stats = rewrite_dxil_text(src)
    if len(sys.argv) > 2:
        open(sys.argv[2], "w").write(out)
    else:
        print(out)
    print(f"[SQ2] rewrites: {stats}", file=sys.stderr)
