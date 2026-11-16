"""Generate H4/H5/H6 hunks for mesa_sq2_instrument.patch.

Reads pristine sources, asserts each anchor appears exactly once, emits
hunks with machine-computed old/new counts. Blank context lines are a
single space (git apply rejects truly-empty ones); file ends with newline.
"""
import sys

REF = "mesa-src-ref2"
OUT = "custom-driver/snippet_v2.patch"

DUMP = """\
+         ID3D12InfoQueue *sq2_iq = nullptr;
+         if (SUCCEEDED({DEV}->QueryInterface(IID_PPV_ARGS(&sq2_iq)))) {{
+            uint64_t sq2_n = sq2_iq->GetNumStoredMessages();
+            fprintf(stderr, "D3D12 SQ2: infoqueue messages=%llu (experimental)\\n", (unsigned long long)sq2_n);
+            uint64_t sq2_first = sq2_n > 8 ? sq2_n - 8 : 0;
+            for (uint64_t sq2_i = sq2_first; sq2_i < sq2_n; ++sq2_i) {{
+               SIZE_T sq2_len = 0;
+               if (SUCCEEDED(sq2_iq->GetMessage(sq2_i, nullptr, &sq2_len)) && sq2_len > 0 && sq2_len < 8192) {{
+                  char *sq2_buf = new char[sq2_len];
+                  if (SUCCEEDED(sq2_iq->GetMessage(sq2_i, (D3D12_MESSAGE *)sq2_buf, &sq2_len)))
+                     fprintf(stderr, "D3D12 SQ2: layer: %s (experimental)\\n", ((D3D12_MESSAGE *)sq2_buf)->pDescription);
+                  delete[] sq2_buf;
+               }}
+            }}
+            sq2_iq->Release();
+         }}"""


def emit(path, func, anchor, new_block_lines, out):
    src = open(f"{REF}/{path}", "r", newline="").read()
    n = src.count(anchor)
    print(f"{func}: anchor found {n}x")
    assert n == 1, f"anchor not unique in {path}"
    old_lines = anchor.split("\n")
    assert old_lines[0] != "" and old_lines[-1] != "", "anchor must not start/end blank"
    old_n = len(old_lines)
    new_n = old_n + len(new_block_lines)
    out.append(f"diff --git a/src/gallium/drivers/d3d12/{path} b/src/gallium/drivers/d3d12/{path}")
    out.append(f"--- a/src/gallium/drivers/d3d12/{path}")
    out.append(f"+++ b/src/gallium/drivers/d3d12/{path}")
    out.append(f"@@ -1,{old_n} +1,{new_n} @@ {func}")
    # reconstruct hunk: anchor lines prefixed with ' ', new lines inserted
    # at the marker position denoted by new_block_lines entries; here the
    # block lists (index_after_anchor_line, [added lines])
    pos, adds = new_block_lines
    for i, ln in enumerate(old_lines):
        if i == pos:
            out.extend(adds)
        out.append(" " + ln if ln else " ")
    if pos == len(old_lines):
        out.extend(adds)
    out.append(" ")


def main():
    out = []
    # H4: capture Close() hresult
    h4_anchor = (
        "   if (FAILED(ctx->cmdlist->Close())) {\n"
        '      debug_printf("D3D12: closing ID3D12GraphicsCommandList failed\\n");\n'
        "      batch->has_errors = true;\n"
        "      return;\n"
        "   }"
    )
    h4_adds = [
        "+   HRESULT sq2_close_hr = ctx->cmdlist->Close();",
        "+   if (FAILED(sq2_close_hr)) {",
    ]
    h4_adds2 = [
        '+      fprintf(stderr, "D3D12 SQ2: cmdlist Close FAILED hr=0x%lx (experimental)\\n", (long)sq2_close_hr);',
    ]
    # H4 needs two insertion points; do it as one hunk manually below.
    # H5 anchor
    h5_anchor = (
        "   if (residency_ok)\n"
        "      screen->cmdqueue->ExecuteCommandLists(count_to_execute, to_execute);\n"
        "   else\n"
        "      batch->has_errors = true;"
    )
    h5_adds = [
        "+   if (residency_ok) {",
        "+      screen->cmdqueue->ExecuteCommandLists(count_to_execute, to_execute);",
        "+      HRESULT sq2_exec_removed = screen->dev->GetDeviceRemovedReason();",
        '+      fprintf(stderr, "D3D12 SQ2: Execute removed=0x%lx (experimental)\\n", (long)sq2_exec_removed);',
        "+      if (sq2_exec_removed != S_OK) {",
    ] + DUMP.format(DEV="screen->dev").split("\n") + [
        "+      }",
        "+   }",
    ]
    # H6 anchor (draw.cpp, after dispatch bookkeeping)
    h6_anchor = (
        "   /* The next draw needs to reassert the graphics PSO */\n"
        "   ctx->cmdlist_dirty |= D3D12_DIRTY_SHADER;\n"
        "   batch->pending_memory_barrier = false;"
    )
    h6_adds = [
        "+   d3d12_flush_cmdlist_and_wait(ctx);",
        "+   {",
        "+      HRESULT sq2_fw_removed = d3d12_screen(ctx->base.screen)->dev->GetDeviceRemovedReason();",
        '+      fprintf(stderr, "D3D12 SQ2: compute dispatch flushed+waited, removed=0x%lx (experimental)\\n", (long)sq2_fw_removed);',
        "+      if (sq2_fw_removed != S_OK) {",
    ] + DUMP.format(DEV="d3d12_screen(ctx->base.screen)->dev").split("\n") + [
        "+      }",
        "+   }",
    ]

    # H4 custom (two insertion points)
    src = open(f"{REF}/d3d12_batch.cpp", "r", newline="").read()
    assert src.count(h4_anchor) == 1
    old = h4_anchor.split("\n")
    new_body = (
        [" " + old[0] + "  // replaced below -- placeholder"]
    )
    # build manually:
    hunk = []
    hunk.append("diff --git a/src/gallium/drivers/d3d12/d3d12_batch.cpp b/src/gallium/drivers/d3d12/d3d12_batch.cpp")
    hunk.append("--- a/src/gallium/drivers/d3d12/d3d12_batch.cpp")
    hunk.append("+++ b/src/gallium/drivers/d3d12/d3d12_batch.cpp")
    hunk.append(f"@@ -310,{len(old)} +310,{len(old) - 1 + 3} @@ d3d12_end_batch")
    hunk.append("-" + old[0])
    hunk.append("+" + h4_adds[0][1:])
    hunk.append("+" + h4_adds[1][1:])
    hunk.append(" " + old[1])
    hunk.append("+" + h4_adds2[0][1:])
    for ln in old[2:]:
        hunk.append(" " + ln if ln else " ")
    out.extend(hunk)

    # H5 via emit with insertion after line index 2 (after Execute line)
    src5 = open(f"{REF}/d3d12_batch.cpp", "r", newline="").read()
    assert src5.count(h5_anchor) == 1
    old5 = h5_anchor.split("\n")
    hunk5 = []
    hunk5.append("diff --git a/src/gallium/drivers/d3d12/d3d12_batch.cpp b/src/gallium/drivers/d3d12/d3d12_batch.cpp")
    hunk5.append("--- a/src/gallium/drivers/d3d12/d3d12_batch.cpp")
    hunk5.append("+++ b/src/gallium/drivers/d3d12/d3d12_batch.cpp")
    hunk5.append(f"@@ -331,{len(old5)} +331,{len(old5) - 2 + len(h5_adds)} @@ d3d12_end_batch")
    hunk5.append("-" + old5[0])
    hunk5.append("-" + old5[1])
    hunk5.extend(h5_adds)
    for ln in old5[2:]:
        hunk5.append(" " + ln if ln else " ")
    out.extend(hunk5)

    # H6
    src6 = open(f"{REF}/d3d12_draw.cpp", "r", newline="").read()
    assert src6.count(h6_anchor) == 1
    old6 = h6_anchor.split("\n")
    hunk6 = []
    hunk6.append("diff --git a/src/gallium/drivers/d3d12/d3d12_draw.cpp b/src/gallium/drivers/d3d12/d3d12_draw.cpp")
    hunk6.append("--- a/src/gallium/drivers/d3d12/d3d12_draw.cpp")
    hunk6.append("+++ b/src/gallium/drivers/d3d12/d3d12_draw.cpp")
    hunk6.append(f"@@ -1,{len(old6)} +1,{len(old6) + len(h6_adds)} @@ d3d12_launch_grid")
    for ln in old6:
        hunk6.append(" " + ln if ln else " ")
    hunk6.extend(h6_adds)
    # trailing context: next two lines of the function
    idx = src6.index(h6_anchor) + len(h6_anchor)
    following = src6[idx:].split("\n")[1:3]
    for ln in following:
        hunk6.append(" " + ln if ln else " ")
    # fix counts: old += trailing
    old_total = len(old6) + len(following)
    new_total = old_total + len(h6_adds)
    hunk6[3] = f"@@ -1398,{old_total} +1398,{new_total} @@ d3d12_launch_grid"
    out.extend(hunk6)

    open(OUT, "w", newline="").write("\n".join(out) + "\n")
    print("wrote", OUT)


main()
