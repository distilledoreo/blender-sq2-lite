# SQ2 on-device results — fork baseline (`none`) + probe table

Date: 2026-11-16. Device: Microsoft SQ2 (Adreno 680), driver 27.20.2140.0.
Builds: CI run 10 (`none`, unpatched fork) and run 12 (`probe`).

## Test 1 — core probe vs inbox baseline: PASS, identical

`wgl_probe_core.py` (core profile, ARM64 Blender python) against fork
`opengl32.dll`, both `none` and `probe` sets:

- Core 4.3: NULL (wall intact). Core 4.1: context OK.
- `RENDERER = D3D12 (Qualcomm(R) Adreno(TM) 680 GPU)` — real GPU, not WARP.
- `VERSION = 4.1 (Core Profile) Mesa 26.3.0 (git-0a6fa60abb)`.
- Ext list (196) is **byte-identical** to the inbox 4.1 list
  (`logs/phase1/d3d12_exts_core41_fork_unpatched.txt`).
- Baseline `none` acceptance row: PASSED.

## Test 2 — Blender launch with unpatched fork: crash reproduced exactly

Gen2-lift Blender 5.2.3 + fork DLLs beside exe + `MESA_GL_VERSION_OVERRIDE=4.3`
+ `MESA_GLSL_VERSION_OVERRIDE=430`:

- Log (`logs/phase1/blender_fork_baseline.log`): GL 4.3 core context on
  Adreno 680, `Successfully hooked OpenGL debug callback`,
  `Using Backend "OpenGL"`, Limited Platform Support notice — then
  `ERROR draw_resource_finalize Linking: Error: no shaders attached to the program`
  followed by `EXCEPTION_ACCESS_VIOLATION`.
- `blender.crash.txt` (`logs/phase1/blender_fork_baseline_crash.txt`):
  read AV at `0x18`, stack `blender::GPU_shader_bind` called from
  `blender::draw::Manager::end_sync` — the documented inbox signature.
- Screenshot (`logs/phase1/blender_fork_gui3_small.png`): main window
  `(Unsaved) - Blender 5.2.3 LTS` up behind the Limited Platform Support
  dialog; crash dialog (`Restart` / `View Crash Log` / `Close`) after sync.
- Conclusion: the fork faithfully reproduces the inbox failure. No new failure
  mode introduced by the fork toolchain.

## Probe table (`probe`, stderr) — first measurement of the gate

`logs/phase1/probe_sm_table.txt`:

```text
D3D12 SQ2: highest shader model 0x61, max feature level 0xc100
D3D12 SQ2: TypedUAVLoadAdditionalFormats=1
D3D12 SQ2: fmt 11 hr=0x0 tuav=1 load=0 store=1
```

Reading:

- SM 0x61 = **Shader Model 6.1**, FL 12_1. SM-gating theory is dead:
  the device compiles SM 6.1; compute is not shader-model limited.
- `TypedUAVLoadAdditionalFormats=1` — the inbox D3D12 runtime reports the
  flag TRUE (earlier "expected false" was wrong; the flag is not the wall).
- The wall is the first format check: `fmt 11` = `R16G16B16A16_UNORM`
  (SDK `dxgiformat.h`: 10 = FLOAT, 11 = UNORM) returns `hr=S_OK`,
  `tuav=1`, but `load=0` → gate returns false at the first entry.
  Only one `fmt` line printed because the probe keeps the early-break.

## Corrections (assessment 2026-11-16)

- `fmt 11` is `R16G16B16A16_UNORM`, not `_FLOAT`. Verified against the
  on-device SDK (`Windows Kits/10/Include/10.0.26100.0/shared/dxgiformat.h`)
  and it is `additional_formats[0]`, matching the probe's first line.
- Extension count is **196**, not 195. Both ext files have 196 `GL_`
  lines; `wc -l` says 195 only because the last line has no trailing
  newline. The probe's own `NUM_EXT: 196` confirms. The "195" was a
  `wc -l` miscount, and the fork-vs-inbox diff was identical files.
- No probe change was needed for the full table: with
  `D3D12_SQ2_FORCE_IMAGES=1` the force path does not return early, so the
  probe's per-iteration `fmt` line prints for all 21 formats. Format
  numbers map 1:1 to names via the SDK enum (table below).

## Force-on results (`both` build, run 43935135410)

Core probe with `D3D12_SQ2_FORCE_IMAGES=1`, **no Mesa version override**:

- `VERSION = 4.2 (Core Profile)`, GLSL 4.20 — natural version bump 4.1 → 4.2.
- `GL_ARB_compute_shader` **present**, `GL_ARB_shader_image_load_store`
  **present**. Ext count 196 → 202 (+6: `ES3_1/ES3_2_compatibility`,
  `compute_shader`, `compute_variable_group_size`, `image_load_store`,
  `image_size`). No `ARB_texture_view` (separate st gate, unforced) — so
  4.3 is not reached, exactly as the version walk predicted.
- Full 21-format table (`logs/phase1/force_sm_table.txt`): **every**
  format reports `hr=0x0 tuav=1 load=0 store=1`. The failure mode is
  uniform — the ONLY missing capability is typed-UAV LOAD.

| # | fmt | DXGI name | load |
|---|-----|-----------|------|
| 0 | 11 | R16G16B16A16_UNORM | 0 |
| 1 | 13 | R16G16B16A16_SNORM | 0 |
| 2 | 16 | R32G32_FLOAT | 0 |
| 3 | 17 | R32G32_UINT | 0 |
| 4 | 18 | R32G32_SINT | 0 |
| 5 | 24 | R10G10B10A2_UNORM | 0 |
| 6 | 25 | R10G10B10A2_UINT | 0 |
| 7 | 26 | R11G11B10_FLOAT | 0 |
| 8 | 31 | R8G8B8A8_SNORM | 0 |
| 9 | 34 | R16G16_FLOAT | 0 |
| 10 | 35 | R16G16_UNORM | 0 |
| 11 | 36 | R16G16_UINT | 0 |
| 12 | 37 | R16G16_SNORM | 0 |
| 13 | 38 | R16G16_SINT | 0 |
| 14 | 49 | R8G8_UNORM | 0 |
| 15 | 50 | R8G8_UINT | 0 |
| 16 | 51 | R8G8_SNORM | 0 |
| 17 | 52 | R8G8_SINT | 0 |
| 18 | 56 | R16_UNORM | 0 |
| 19 | 58 | R16_SNORM | 0 |
| 20 | 63 | R8_SNORM | 0 |

(all with `hr=S_OK tuav=1 store=1`; enum values from the on-device SDK.)

## Force-on Blender launch (Solid)

Recipe: `both` DLLs + `D3D12_SQ2_FORCE_IMAGES=1` + 4.3/430 override.
Log: `logs/phase1/blender_force.log`, crash: `logs/phase1/blender_force_crash.txt`.

- The force table prints in full, then Blender proceeds PAST the old
  failure: **no `draw_resource_finalize` error** — the link failure is gone.
- First new failure (~8s in): `WARNING draw_command_generate
  ComputeShader`, then `ERROR GL_OUT_OF_MEMORY in glBufferData`, then
  `ERROR GL_INVALID_VALUE in glBufferSubData(offset 0 + size 288 > buffer
  size 0)` — Blender now issues compute dispatches; a buffer allocation
  returns size 0 and the follow-up write is rejected.
- Terminal crash moves with it: read AV at `0x4C` in
  `libgallium_wgl.dll!mesa_glapi_get_proc_address` during
  `st_screen_destroy` (teardown after the GL errors), instead of the old
  `blender.exe!GPU_shader_bind ← Manager::end_sync` at `0x18`.
- No viewport rendered: the crash lands during startup sync, before first
  frame. As expected, a clean launch would have said nothing about image
  loads — compute-only was never the claim; the failure arriving one
  stage later (buffer alloc under compute dispatch) is the new datum.
- EEVEE outlook per the assessment: with the flag true, the guaranteed-
  load group covers `SFLOAT_16_16_16_16`, `SFLOAT_32_32_32_32`,
  `SFLOAT_16`, `SFLOAT_32`/`SINT_32`/`UINT_32`; the two EEVEE formats in
  the optional table are `UNORM_16_16` and `UFLOAT_11_11_10`, both
  32-bit texels (the existing cast-lowering case). Inference until the
  per-format fix is measured — next step is that fix, not more force runs.

## Ordered next steps — results (`instrument` build, run 43938927551)

### Code verification (on-device winerror.h) — CORRECTION

Checked against `Windows Kits/10/Include/10.0.26100.0/shared/winerror.h`:

- `0x887A0005` = `DXGI_ERROR_DEVICE_REMOVED`
- `0x887A0001` = `DXGI_ERROR_INVALID_CALL`
- `0x887A0006` = `DXGI_ERROR_DEVICE_HUNG`

The earlier record is corrected: `removed=0x887a0001` is **INVALID_CALL**,
not DEVICE_HUNG. There is **no DEVICE_HUNG evidence anywhere** — the row-1
inference from the previous turn is withdrawn. The terminal line reads:
create fails with DEVICE_REMOVED while the reason query returns
INVALID_CALL — an odd combo the debug layer was supposed to explain (see
below). `usage=0` = `PIPE_USAGE_DEFAULT`, `bind=0x8` =
`PIPE_BIND_SAMPLER_VIEW`, `target=2` = `PIPE_TEXTURE_2D` (26.3.0
`p_defines.h`): the failing create is a sampled 2D texture, fallout on an
already-bad device, not the root cause.

### 1. Instrumented failure (logs: `logs/phase1/blender_instrument*.log`)

Build `instrument` = msvc + probe + force applier + `mesa_sq2_instrument.patch`
(buffer-create failure print; compute PSO + dispatch checkpoints). Blender
launch recipe identical to the force run (force env + 4.3/430 override).

- `compute PSO created, removed=0x0` — pipeline creation succeeds.
- `compute dispatch #1 grid=1x1x1 indirect=0 removed=0x0` — exactly ONE
  dispatch is ever recorded, device healthy at record time.
- Then the known cascade: `draw_command_generate ComputeShader` compiles,
  `GL_OUT_OF_MEMORY in glBufferData` ×N, `GL_INVALID_VALUE in
  glBufferSubData` (sizes 288, 96 over buffer 0).
- Terminal `resource create FAILED hr=0x887a0005 size=32 bind=0x8
  usage=0 target=2 removed=0x887a0001`: hr = `DXGI_ERROR_DEVICE_REMOVED`,
  reason = `0x887a0001` = `DXGI_ERROR_DEVICE_HUNG`.
- Enum decode (26.3.0 `p_defines.h`): bind `0x8` = `PIPE_BIND_SAMPLER_VIEW`,
  target `2` = `PIPE_TEXTURE_2D`, usage `0` = `PIPE_USAGE_DEFAULT`. This is
  a sampled 2D texture, not a compute buffer/SSBO (those are
  `SHADER_BUFFER`/`SHADER_IMAGE`) — it is fallout on an already-hung device,
  not the root cause. Likewise the early OOMs come from the buffer-manager
  path, not `create_or_place` (which printed only this once, at the end).
- Crash signature unchanged from the force run: read AV at `0x4C` in
  `libgallium_wgl!mesa_glapi_get_proc_address` during `st_screen_destroy`
  (`logs/phase1/blender_instrument_crash.txt`).
- SUPERSEDED by v2/v3 below: the flush+fence-wait proves the dispatch
executed fine, and the reason code was misread (see correction above —
INVALID_CALL, no HUNG anywhere).

### 1b. Instrument v2/v3 — first failing Close/Execute (log:
`logs/phase1/blender_instrument2.log`, build `instrument` run 43972184797)

v2 added: Close() HRESULT, removal after every ExecuteCommandLists,
forced flush+fence-wait after each compute dispatch, ID3D12InfoQueue dump
on nonzero removal. v3 added: pre-dispatch recording print, end_batch
entry print (H8 had to move to the python applier — `git apply` rejects
its byte-identical pre-image, the same quirk as the force hunk).

Blender frame result — the exact sequence around the failure:

```text
compute PSO created, removed=0x0
recording dispatch grid=1x1x1 indirect=0
compute dispatch #1 grid=1x1x1 indirect=0 removed=0x0
end_batch enter / Execute removed=0x0
compute dispatch flushed+waited, removed=0x0     <- compute fully done, healthy
end_batch enter / Execute removed=0x887a0001     <- NEXT submit: INVALID_CALL
WARNING draw_command_generate ComputeShader  (00:10.719)
ERROR GL_OUT_OF_MEMORY in glBufferData ...
```

- **No Close ever FAILED**; every pre-compute Execute reports `0x0`.
- The compute batch is exonerated: recorded, flushed, fence-waited,
device healthy throughout. The v1 build (no forced flush) shows the
identical OOM cascade, so the flush instrumentation is innocent.
- The fault is the **first submit after the first compute batch**
(or state that batch leaves behind): INVALID_CALL on Execute, then the
OOM cascade, then the terminal DEVICE_REMOVED create + teardown AV.
Blender-side, this lands between the workbench-prepass compiles and the
draw_command_generate compile.
- No nonzero removal anywhere else in the run.

### Minimal compute test (no Blender: `mesa-test/compute_min.py`)

Force-on 4.2 core ctx, no override: one SSBO (4xuint, zeroed), compute
shader writing `data[i] = i*7+1` via `gl_GlobalInvocationID`, dispatch
1x1x1, barrier, glFlush, glFinish, readback. (Needed
`#extension GL_ARB_compute_shader/shader_storage_buffer_object` in a
`#version 420` shader — 4.2 GLSL gates both.)

- Compile OK, link OK, dispatch call returns, then **AV (NULL read)
inside glFlush/glFinish**. v3 instrumentation: 3 healthy
end_batch+Execute cycles, `compute PSO created`, then crash **before**
the `recording dispatch` print — i.e. in the record path (root
signature / descriptor / Dispatch recording), not in submit.
- This differs from Blender (which records dispatches fine): the minimal
test binds an SSBO (`PIPE_BIND_SHADER_BUFFER`), Blender's first dispatch
may not. The record-path AV with SSBO bound is a second, distinct lead —
not yet reduced (no-SSBO variant untested).
- Per the decision table this is neither "passes" nor HUNG/INVALID_CALL:
no GL error, no removal, just a record-path NULL AV. It needs the layer
to name the call — which is blocked (next).

### Validated minimal test + WARP + bisect + debug-hr (build `instrument` run 43976031237)

- **Validated test** (`mesa-test/compute_min_validated.py`): full
`argtypes`/`restype` on every GL call (64-bit-safe `GLsizeiptr`/`GLintptr`),
`glGetError` after every call, `GL_BUFFER_SIZE` read back per buffer, and
**three SSBOs** mirroring `end_sync` (shader touches bindings 0,1,2).
Result: all sizes 16, zero GL errors — then the **same AV in `glFlush`**
before the recording-dispatch print, with three fence-verified healthy
submits (`bisect-wait removed=0x0`) ahead of it. The ctypes-truncation
and zero-size-buffer variants of the test-defect hypothesis are refuted;
the record-path AV is real and CPU-side. Blender's disagreement (it
records dispatches fine) stands unexplained — something else differs
between its dispatch and the minimal one.
- **WARP control — blocked on-device.** `MESA_D3D12_DEFAULT_ADAPTER_NAME`
is real (Mesa docs; case-insensitive substring) but has **no effect on
this WGL path**: UNSET/Basic/WARP/Adreno all yield `D3D12 (Qualcomm(R)
Adreno(TM) 680 GPU)`. `LIBGL_ALWAYS_SOFTWARE=1` (the EnumWarpAdapter
branch) yields **no context at all** with empty stderr. There is no
working WARP D3D12 device on this machine, so no table row can be
checked that way.
- **Bisect names the failing submit** (log `logs/phase1/blender_bisect.log`):
compute batch = submit `...665`, flushed+waited `0x0`; the **very next
submit `...666` reports `INVALID_CALL` on Execute and the fence-wait
confirms it**. First failing operation, exactly attributed. Blender-side
it lands right after the `draw_command_generate ComputeShader` compile
warning, before the OOM cascade. What that submit contains (graphics
root-sig / heap / PSO restore after compute) is the next trace.
- **Graphics Tools INSTALLED; debug layer still unusable — root-caused
to device creation, both doors measured shut** (build `instrument` run
43982549115, H5 CreateDevice prints):
  - `DISM /Online /Add-Capability ...Tools.Graphics.DirectX...` completed
(elevated, two attempts — first timed out at ~38%, second finished;
`D3D12SDKLayers.dll` now in System32).
  - Factory + debug: `debug via factory hr=0x0` (interface obtained!),
`debuglayer flag=1`, then `factory CreateDevice GENERIC hr=0x80070057`
(E_INVALIDARG) and `11_0 hr=0x80070057`, `dev=NULL` — the factory
rejects NULL-adapter creation with the layer on.
  - Singleton + debug (`D3D12_DEBUG="debuglayer,singleton"`):
`D3D12GetDebugInterface hr=0x0`, `factory=NULL`, still NO_CTX (else-branch
uninstrumented). Raw re-measurement (`d3d12_fl_probe.py`, this turn):
`D3D12CreateDevice(NULL)` → `0x80004002` (E_NOINTERFACE) at
12_1/12_0/11_1/11_0 (12_2 → `0x887A0004` unsupported, as expected).
  - So the layer is installed and reachable but unusable through either
of Mesa's device paths without explicit-adapter surgery. Bisect (submit
...666) stands in as the attribution, as authorized.
- **Symbolized stack: PDBs ship in the CI artifact** (`*.pdb` uploaded
since run 43976031237) but no faulting function+line yet — the Blender
crash.txt trace is unchanged (teardown `get_proc_address` AV), and the
minimal-test record-path AV yields no address via ctypes. Next: finer
record-path prints (between PSO-created and recording-dispatch) or
DbgHelp `SymFromAddr` against the artifact PDB.

### Debug layer — blocked (original note)

- `D3D12_DEBUG=debuglayer` (confirmed token in 26.3.0 source) **kills
context creation entirely** (no 4.2 ctx, driver never inits) — even with
the full Agility 619 redist (D3D12Core + SDKLayers) staged exe-relative
and `D3D12_AGILITY_*` set.
- Graphics Tools FOD presence/install requires elevation
(`Get-WindowsCapability` refuses); not available in this session.
- So there is no debug-layer message and the InfoQueue dump code ships
dormant in the build (prints nothing without the layer). The layer names
nothing until it can run.
- First failing Close/Execute stands as the attribution instead: no
failing Close exists; the first failing operation device-wide in
Blender's frame is the Execute right after the successful compute batch.

### 2. Launch conditions — stated

The force and instrument Blender runs used `MESA_GL_VERSION_OVERRIDE=4.3`
+ `MESA_GLSL_VERSION_OVERRIDE=430` (see `Version: 4.3 (Core Profile)` in
both logs). The natural no-override context with force is **4.2**. Blender
requests 4.3; under the override it gets a reported-4.3 context on a 4.2
driver. A no-override Blender launch on the forced 4.2 driver is untested.

### 3. Last successful step

`draw_command_generate ComputeShader` is a COMPILE notification (same
`WARNING <name> <stage>:` pattern as the two VertShader lines above it),
not a dispatch. Last completed record: compute dispatch #1 (1x1x1,
`removed=0x0`). Last completed GPU-side execution: unknown (deferred
cmdlist) — the first observable failure is `GL_OUT_OF_MEMORY in
glBufferData` immediately after the compile line.

### 4. Agility + force-on — version recorded

- Gate confirmed: `st_extensions.c:1111`
  `EXT_CAP(ARB_texture_view, sampler_view_target)`;
  `d3d12_screen.cpp:417` sets `sampler_view_target =
  opts12.RelaxedFormatCastingSupported` from the `D3D12_OPTIONS12` query.
- Force + Agility SDK 1.619.5 (full redist: Core + SDKLayers, exe-relative
  next to the loading exe): core probe reports **4.2, 202 exts, compute
  present, no `ARB_texture_view`** — identical to force on the inbox
  runtime. Absolute-path and exe-relative layouts agree; the earlier
  "Agility 4.1" test ran with the image gate closed so it could not show
  this. QC caps do not include relaxed format casting on this driver.
- mmozeiko's "inbox 4.2, Agility 4.6" remains unexplained by caps here —
  left as an open discrepancy, not a contradiction of the measurement.

### 5. Texture views on the Solid path under the override

`blender.exe` references `glTextureView` (×1) and `GPU_texture_create_view`
(×1). With the 4.3 override, Blender resolves the core-4.3 entry point on
a driver that does not expose `ARB_texture_view`. Whether the Solid path
actually calls it before the compute failure is not yet in the logs — the
run dies in startup sync first. Flagged for the per-format-fix runs.
