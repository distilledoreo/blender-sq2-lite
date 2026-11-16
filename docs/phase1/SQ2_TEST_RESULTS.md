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
- The wall is the first format check: `fmt 11`
  (`DXGI_FORMAT_R16G16B16A16_FLOAT`) returns `hr=S_OK`, `tuav=1`,
  but `load=0` (CheckFormatSupport lacks `TYPED_UNORDERED_ACCESS_VIEW`
  for this format) → `can_shader_image_load_all_formats` returns false at
  the first entry → st gate keeps `ARB_compute_shader` (and images) off.
- Only one `fmt` line printed: the probe keeps the early-break, so the
  remaining 20 formats are still UNMEASURED. The `both` build (force path
  logs every failed format it forces past) will enumerate them.

## Next

`both` build → on-device force-on test (`D3D12_SQ2_FORCE_IMAGES=1`):
expect `ARB_compute_shader` in core ctx + full failed-format list on stderr,
then Blender launch to see whether the crash signature changes.
