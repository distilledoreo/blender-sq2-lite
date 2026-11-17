# Mesa d3d12: post-compute 16-byte readback submit fails on Adreno 680 (SQ2)

Draft for https://gitlab.freedesktop.org/mesa/mesa/-/issues/new — component
**Drivers/D3D12**. Corrections applied after review: "probable" (not
confirmed) driver defect; WARP passed the failing point but never drew a
frame; the debug-layer failure also happens on WARP, so it is not
Adreno-specific; `heap=4` is `D3D12_HEAP_TYPE_CUSTOM` and says nothing about
which heap; read-back through the staging-copy path **has** since been shown
to succeed on this Adreno in a Blender-free probe.

---

## Title

d3d12: `CopyBufferRegion` in a post-compute batch fails with `0x887a0001`
on Adreno 680 (Snapdragon 8cx Gen 2 / Surface Pro X SQ2); identical copy
shape succeeds in a standalone probe and on WARP

## Environment

- Mesa 26.3.0 (tag `mesa-26.3.0`, commit `0a6fa60abb`), built from the tag:
  `-Dgallium-drivers=d3d12 -Dllvm=disabled -Dplatforms=windows`, MSVC arm64,
  release.
- Windows 11 24H2 (10.0.26100), ARM64.
- GPU: Qualcomm(R) Adreno(TM) 680 GPU, driver **27.20.2140.0**
  (`ACPI\VEN_QCOM&DEV_043A&SUBSYS_MSWW8180`, Surface Pro X SQ2).
  Windows Update offers no newer display driver for this machine; the only
  pending driver update is an audio APO.
- Blender 5.2.3 LTS, WGL, `--factory-startup --debug --debug-gpu`,
  `GALLIUM_DRIVER=d3d12`, `MESA_GL_VERSION_OVERRIDE=4.3`,
  `MESA_GLSL_VERSION_OVERRIDE=430`.

## Summary

Drawing the default scene fails at a submit whose contents are two draws and
one 16-byte `CopyBufferRegion` from a device-local buffer into a staging
buffer. `ID3D12CommandQueue::ExecuteCommandLists` fails with
`0x887a0001`; the next call on that queue fails and Blender exits. The device
is **not** removed: `GetDeviceRemovedReason` returns `S_OK` before the submit
and `0x0` in every earlier batch.

The failure is **probably driver-side, but not confirmed**: the copy is legal
in isolation on this same GPU (see "Standalone probe" below), the same command
stream completes on WARP, and no Mesa state tracking anomaly is visible in the
instrumented log.

## Failing submit contents

Isolation method: flush + fence-wait inserted between commands (patch, not
upstream). The failing batch is the first one after a compute dispatch whose
result is read back.

Preceding submit — healthy, `Execute` → `S_OK`, fence-waited:

```
draw  mode=6 count=4 indexed=0      (triangle fan, u_primconvert)
draw  mode=4 count=6 indexed=1      (draw_range_elements)
recording dispatch grid=1x1x1 indirect=0
compute dispatch #1                 removed=0x0
flush / end_batch / Execute -> 0x0  flushed+waited, removed=0x0
```

Failing submit:

```
draw  mode=6 count=4 indexed=0      (identical to the healthy one above)
draw  mode=4 count=6 indexed=1
transition A before=0x0 after=0x800 (COPY_SOURCE)
transition B before=0x0 after=0x400 (COPY_DEST)
copybuf  width=16
Execute -> 0x887a0001
```

Copy parameters, printed inside `transfer_buf_to_buf` (scratch patch):

```
width=16  same_resource=0
src: width0=16   heap type=4 (CUSTOM, i.e. Mesa placed resource)
dst: width0=256  heap type=4 (CUSTOM)
src_offset=0  dst_offset=0  src_suballoc=0  dst_suballoc=0
```

`D3D12_HEAP_TYPE_CUSTOM` is what Mesa uses for every resource here, so the
heap type does not distinguish these resources; it is reported only for
completeness. Both offsets are 0, the copy is 16 bytes from a 16-byte buffer
into a 256-byte buffer, the two resources are distinct, and both are
transitioned to `COPY_SOURCE`/`COPY_DEST` in the same command list
immediately before the copy.

Earlier in the same session, 114 copies of the mirror shape (upload,
`PIPE_MAP_WRITE`, `src_w=256 -> dst_w=16`) run on the Adreno and all succeed.
The failing copy is the first **readback** copy of the session.

## Standalone probe (Blender-free) — does NOT reproduce

A minimal WGL probe on the same Adreno, same DLLs, no compute and no draws:
`glBufferData(16)`, `glGetBufferSubData` ×3, `glBufferSubData` + read,
`glMapBufferRange(GL_MAP_READ_BIT)`, for both `GL_ARRAY_BUFFER` and
`GL_UNIFORM_BUFFER`. All reads return the expected bytes and
`glGetError() == 0` throughout.

Instrumented transfer prints show the staging-copy path itself working on
this GPU, including two `map-read` copies of exactly the failing shape:

```
copycaller map-read  src_w=16 dst_w=256  src_off=0 dst_off=512   Execute 0x0
copycaller map-read  src_w=16 dst_w=256  src_off=0 dst_off=4608  Execute 0x0
copycaller map-write (x8) src_w=256 dst_w=16                     Execute 0x0
```

So the path, the shape and the direction are all fine in isolation; what the
probe does not reproduce is the application state around them (a compute
dispatch immediately before, a long-lived context with many prior batches,
and the specific staging buffer history).

## WARP comparison

With an adapter-selection patch (`D3D12_SQ2_ADAPTER=Basic`) the same Mesa
build runs the same scene on the Microsoft Basic Render Driver. The failing
submit — same draws, same 16-byte map-read copy of the same shape — executes
`0x0`, and the session continues through further compute dispatches
(#6, #7) and further pad-read copies without error.

Caveat: WARP is much slower here, and the run was stopped by a timeout while
still compiling shaders. **No frame was rendered or confirmed on WARP** — the
result is that WARP passes the failing submit, not that it draws the scene.

## Debug layer and DRED

- The d3d12 debug layer cannot be created on this machine: with
  `CreateDXGIFactory2(DXGI_CREATE_FACTORY_DEBUG)` the factory is created and
  the debug interface is obtained, but `D3D12CreateDevice` returns
  `E_INVALIDARG` for both `D3D_FEATURE_LEVEL_1_0_GENERIC` and `11_0`, and
  Blender exits before any submit.
- This also happens with the **WARP** adapter selected, so it is not specific
  to the Adreno driver and provides no evidence either way; it just means no
  layer message exists for this failure.
- DRED is unavailable on this driver:
  `ID3D12DeviceRemovedExtendedDataSettings` QI returns `E_NOINTERFACE`
  (`0x80004002`); breadcrumb/page-fault calls return `0x887a0004`.

## Extra data points

- Forcing flush + fence wait after every compute dispatch does not avoid the
  failure; splitting after every draw or copy does not either.
- Skipping the compute dispatch avoids it, but then the scene has nothing to
  render the same way, so that is not a clean control.

## Question

Given that the same `CopyBufferRegion` (same shape, same direction, same
suballoc'd resources) executes correctly in a standalone probe on this GPU,
but fails when it follows a compute dispatch inside a long-lived application
context, is this a known Adreno/WDDM issue with a copy-to-staging batch
scheduled right after a compute batch — e.g. retained compute state, a
missing UAV barrier, or reuse of an upload staging buffer as the readback
source? And is there a driver-agnostic mitigation `d3d12` could apply, such
as a UAV barrier before the copy, a different staging-buffer pool for readback
after compute, or a full queue flush between compute and transfer batches?

Logs (instrumented build; every submit, transition and copy printed):
`blender_build2_run1_err.txt` (Adreno), `blender_build2_run2_err.txt` (WARP),
`sq2_readback_probe_control_out.txt` (standalone probe).
