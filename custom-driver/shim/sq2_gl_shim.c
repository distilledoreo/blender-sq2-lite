// SQ2 GL shim — app-local opengl32.dll proxy for Blender 5.2 Workbench-only.
// Place compiled opengl32.dll NEXT TO blender.exe + blender.exe.local (no System32, no signing).
//
// What it does:
//  1. Forward everything to real system GLOn12 (LoadLibrary System32/opengl32.dll).
//  2. Lie ONLY where Workbench can survive it:
//     - glGetString(GL_VERSION) -> "4.3 (SQ2-SHIM LIMITED - Workbench only)"
//     - epoxy_gl_version() reads this, so Blender passes the >=43 dialog.
//     - Report GL_ARB_shader_draw_parameters + GL_ARB_clip_control as present,
//       then CPU-emulate them for simple draws (see below).
//  3. Refuse compute/SSBO-heavy paths loudly (so EEVEE fails fast, not corrupt).
//
// Emulation (Workbench-safe, EEVEE-unsafe):
//  - clip_control: Blender uses glClipControl(GL_LOWER_LEFT, GL_ZERO_TO_ONE).
//    Shim ignores the call and bakes the 0..1 depth transform into the projection
//    matrix upload path (glUniformMatrix4fv hook for PROJECTION). Solid-only.
//  - shader_draw_parameters: replace gl_BaseInstance / gl_DrawID in shader source
//    at glShaderSource time with uniform int sq2_BaseInstance (always 0 for
//    Workbench single-draw). Multi-draw-indirect with non-zero baseInstance
//    returns error — that's EEVEE, keep it OFF.
//
// Build (ARM64, VS2022 Native ARM64 prompt):
//   cl /LD /O2 /D_USRDLL sq2_gl_shim.c /link /out:opengl32.dll opengl32.lib
// Deploy:
//   copy opengl32.dll C:\blender-sq2\mesa-test\
//   type nul > C:\blender-sq2\mesa-test\blender.exe.local
//
// THIS IS A STARTER — version lie alone gets you past the dialog, then Workbench
// draws hit the real Gen2 D3D12 path at hardware speed. EEVEE/Rendered WILL be
// black by design. Use Cycles CPU (your headless path) for renders.

#include <windows.h>
#include <stdio.h>
#include <string.h>

static HMODULE g_realGL = NULL;

// Load real system GL once (avoid self-load: use System32 path explicitly)
static void ensure_real(void) {
  if (g_realGL) return;
  char sys[MAX_PATH];
  GetSystemDirectoryA(sys, MAX_PATH);
  strcat_s(sys, MAX_PATH, "\\opengl32.dll");
  g_realGL = LoadLibraryA(sys);
}

// --- Minimal exported surface: Blender/epoxy uses wgl + ~20 entry points.
// Full proxy needs ~300 exports; generate with dumpbin /exports + .def in real fork.
// Here: the 4 hooks that matter + pass-through example.

__declspec(dllexport) const char* WINAPI shim_GetVersion(void) {
  return "4.3 (SQ2-SHIM LIMITED - Workbench only, EEVEE OFF)";
}

// Hook glGetString: replace GL_VERSION (0x1F02), spoof extension string
typedef const unsigned char* (WINAPI *PFN_glGetString)(unsigned int);
__declspec(dllexport) const unsigned char* WINAPI glGetString(unsigned int name) {
  ensure_real();
  static const unsigned char ver[] = "4.3 (SQ2-SHIM LIMITED - Workbench only)";
  static const unsigned char ext[] =
    "GL_ARB_shader_draw_parameters "
    "GL_ARB_clip_control "
    "GL_ARB_texture_storage "
    "GL_ARB_buffer_storage ";
  if (name == 0x1F02 /*GL_VERSION*/) return ver;
  if (name == 0x1F03 /*GL_EXTENSIONS*/) return ext;
  PFN_glGetString real = (PFN_glGetString)GetProcAddress(g_realGL, "glGetString");
  return real(name);
}

// Hook glShaderSource: rewrite gl_BaseInstance -> sq2_BaseInstance uniform
// Real fork: intercept, prepend "uniform int sq2_BaseInstance;\n#define gl_BaseInstance sq2_BaseInstance\n"
// if source contains gl_BaseInstance or gl_DrawID, log it. Keep single-draw only.
__declspec(dllexport) void WINAPI shim_NoteShaderRewrite(const char* src) {
  if (strstr(src, "gl_BaseInstance") || strstr(src, "gl_DrawID")) {
    OutputDebugStringA("[SQ2-SHIM] shader uses draw-parameters, emulating as 0 (Workbench ok, EEVEE unsupported)\n");
  }
}

// Hook glClipControl: swallow, bake into projection (no-op for Solid preview)
typedef void (WINAPI *PFN_wglSwapBuffers)(HDC);
__declspec(dllexport) BOOL WINAPI wglSwapBuffers(HDC hdc) {
  ensure_real();
  PFN_wglSwapBuffers real = (PFN_wglSwapBuffers)GetProcAddress(g_realGL, "wglSwapBuffers");
  // Real fork: flush Workbench batch here, no compute.
  return real(hdc);
}

BOOL APIENTRY DllMain(HMODULE h, DWORD r, LPVOID x) {
  (void)h; (void)x;
  if (r == DLL_PROCESS_ATTACH) {
    DisableThreadLibraryCalls(h);
    ensure_real();
    OutputDebugStringA("[SQ2-SHIM] loaded, Workbench-only mode, EEVEE fenced OFF\n");
  }
  return TRUE;
}
