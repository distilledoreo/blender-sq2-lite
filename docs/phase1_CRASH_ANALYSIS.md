# Crash analysis: GPU_shader_bind NULL+0x18 (2026-11-16, Gen2-lift + Mesa d3d12 + 4.3 override)

## What the crash is
- `EXCEPTION_ACCESS_VIOLATION` read of `0x18` with `this=NULL` in `GPU_shader_bind(gpu::Shader *gpu_shader)` (`source/blender/gpu/intern/gpu_shader.cc:380`, v5.2.3).
- First deref is `shader->constants` (the `is_empty()` assert path) / `shader->bind()`. Null `gpu_shader` means a shader **failed to create** (compile/link returned nullptr) and `draw::Manager::end_sync` bound it anyway during `DRWContext::engines_init_and_sync` — the first viewport draw.
- Loaded modules confirm the run used app-local Mesa: bare `OPENGL32.DLL` (no version resource = Mesa 26.3 build) + `d3d12.dll` + inbox `D3D12Core.dll` + `qcdx12arm64xum8180.dll` + `dxilconv` + Qualcomm compiler.

## What it proves (and corrects)
- Dialog survival was not viewport success. With the 4.3 override, context creation + gate pass, but the first real draw binds a null shader. This is the predicted "first real failure": override advertises 4.3 while Mesa reports 4.1 (no compute, no images), so a 4.3/compile-dependent shader fails.
- Not a Mesa bug per se: Mesa correctly exposed 4.1. The override lied; Blender believed it.

## Next evidence needed (one re-run)
- Run `SQ2_CAPTURE_CRASH.bat`. It saves `%TEMP%\blender\debug_logs\sq2_crash_run_out.txt` with `--debug --debug-gpu --log cycles`.
- Send `sq2_crash_run_out.txt` + `blender.crash.txt`. The stdout log will contain the failing shader name + GLSL compile error just before the crash (e.g. compute/image/SSBO feature). That single error line selects the fix:
  - Compute-shader creation failure -> Solid culling fallback question.
  - Image/SSBO GLSL failure -> TypedUAV lowering scope.
  - Single engine shader (overlay/workbench) -> possible targeted Blender-side guard instead of Mesa work.
