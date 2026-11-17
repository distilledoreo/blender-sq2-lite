# Mesa d3d12: post-compute 16-byte buffer readback submit fails on Qualcomm Adreno 680 (SQ2)

Ready-to-file report. Not yet filed: filing needs a gitlab.freedesktop.org
account (no CLI/token on this machine). Paste into
https://gitlab.freedesktop.org/mesa/mesa/-/issues/new with component
**Drivers/D3D12**.

---

## Title

d3d12: `CopyBufferRegion` to a staging buffer fails with `0x887a0001`
(E_INVALIDARG/DXGI invalid call) after a compute dispatch on Adreno 680
(Snapdragon 8cx Gen 2 / Microsoft SQ2), identical stream works on WARP

## Environment

- Mesa 26.3.0 (tag `mesa-26.3.0`, commit `0a6fa60abb`), built from the tag
  with `-Dgallium-drivers=d3d12 -Dllvm=disabled -Dplatforms=windows`,
  MSVC arm64, release.
- Windows 11 24H2 (10.0.26100), ARM64.
- GPU: Qualcomm(R) Adreno(TM) 680 GPU, driver 27.20.2140.0
  (ACPI\VEN_QCOM&DEV_043A&SUBSYS_MSWW8180, Surface Pro X SQ2).
- Application: Blender 5.2.3 LTS, WGL, `--factory-startup --debug --debug-gpu`,
  `GALLIUM_DRIVER=d3d12`, `MESA_GL_VERSION_OVERRIDE=4.3`,
  `MESA_GLSL_VERSION_OVERRIDE=430`.

## Summary

Rendering a frame fails at a submit whose only contents are two draws and one
16-byte `CopyBufferRegion` from a device-local buffer into a staging buffer.
`ID3D12CommandQueue::ExecuteCommandLists` returns
`0x887a0001` and the next call on that queue fails; the device is **not**
removed (`GetDeviceRemovedReason` stays `S_OK` before and after).

The same command stream, same Mesa build, same driver switches runs to
completion on the WARP adapter (`D3D12_SQ2_ADAPTER=Basic` →
Microsoft Basic Render Driver), including this exact copy and later
copies of the same shape. Plain buffer readback (no compute, no draws)
also works on the Adreno, so the readback path itself is fine.

## What the failing submit contains

Isolated by flushing + fence-waiting between commands. Numbering is per
recording batch; the failing batch is the first one after a compute dispatch
whose result is read back.

Preceding submit (healthy, `Execute` → `S_OK`, fence-waited):

```
1395: draw  mode=6 count=4 indexed=0     (triangle fan, u_primconvert)
1396: draw  mode=4 count=6 indexed=1     (draw_range_elements)
      recording dispatch grid=1x1x1 indirect=0
      compute dispatch #1  removed=0x0
      flush / end_batch / Execute -> 0x0 / flushed+waited, removed=0x0
```

Failing submit:

```
1395: draw  mode=6 count=4 indexed=0     (identical to the healthy one)
1396: draw  mode=4 count=6 indexed=1
      transition res=A before=0x0 after=0x800  (COPY_SOURCE)
      transition res=B before=0x0 after=0x400  (COPY_DEST)
      copybuf  width=16
      Execute -> 0x887a0001
```

Copy parameters (printed from inside `transfer_buf_to_buf`):

```
width=16  same_resource=0
src resource A: width0=16   heap=D3D12_HEAP_TYPE_DEFAULT(1)
dst resource B: width0=256  heap=D3D12_HEAP_TYPE_DEFAULT(1)
src_offset=0  dst_offset=0  src_suballoc=0  dst_suballoc=0
```

Both offsets are 0, the copy is 16 bytes from a 16-byte buffer into a
256-byte buffer, the two resources are distinct, and both are transitioned
explicitly to `COPY_SOURCE`/`COPY_DEST` in the same command list immediately
before the copy. The 1x1x1 dispatch completes and is fence-waited before this
batch starts.

## Mirror copies that pass

Earlier in the same session, 114 copies of the identical shape run the other
way (upload, `PIPE_MAP_WRITE`), all on the Adreno, all `Execute` → `S_OK`:

```
width=16  src_w=256  dst_w=16  heaps 1/1  offsets 0/0
```

The failing copy is the **first readback copy of the session** and the only
one with `src_w=16 dst_w=256`. Nothing in the parameters distinguishes it
from the passing ones other than direction and which buffer is source.

## Steps to reproduce

1. Windows 11 on Surface Pro X (SQ2), Adreno 680 driver 27.20.2140.0.
2. Install a d3d12-enabled Mesa opengl32.dll/libgallium_wgl.dll beside
   Blender 5.2.3.
3. `set GALLIUM_DRIVER=d3d12` / `MESA_GL_VERSION_OVERRIDE=4.3` /
   `MESA_GLSL_VERSION_OVERRIDE=430`.
4. `blender.exe --factory-startup --debug --debug-gpu --log cycles`.
5. The default scene fails while drawing the first frame; Blender exits.

Setting `D3D12_SQ2_ADAPTER=Basic` (patch adding adapter-name selection) runs
the same frame on WARP without error.

## Extra data points

- The d3d12 debug layer cannot be created on this machine at all:
  `D3D12CreateDevice` returns `E_INVALIDARG` for
  `D3D_FEATURE_LEVEL_1_0_GENERIC` and for `11_0`, both with and without the
  debug factory. So no layer message is available.
- DRED is unavailable: `ID3D12DeviceRemovedExtendedDataSettings` QI returns
  `E_NOINTERFACE` (0x80004002); breadcrumb/page-fault calls return
  `0x887a0004` (unsupported).
- Forcing a `flush + fence wait` after every compute dispatch does not avoid
  the failure; splitting after every draw/copy does not either. Omitting the
  compute dispatch avoids it entirely (the scene then has no compute).
- A plain readback probe (create context, `glBufferData(16)`,
  `glGetBufferSubData` ×3, `glBufferSubData` then read, `glMapBufferRange`
  read; both `GL_ARRAY_BUFFER` and `GL_UNIFORM_BUFFER`) returns correct bytes
  and `glGetError() == 0` on the same Adreno with the same DLLs.

## Question

Given that the copy is legal in isolation, passes on WARP, and that all
Mesa-side state tracking reports the expected transitions, is this a known
Adreno/WDDM issue with `CopyBufferRegion` immediately after a compute batch
(retained compute state / barrier handling), and is there a
driver-agnostic workaround in `d3d12` we should apply — e.g. flushing the
compute batch differently, inserting a UAV barrier before the copy, or
avoiding reuse of the upload staging buffer as the readback source?

Full logs (instrumented build, every submit, transition and copy printed):
`logs/phase1/blender_build2_run1_err.txt` (Adreno) and
`logs/phase1/blender_build2_run2_err.txt` (WARP).
