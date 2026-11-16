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
