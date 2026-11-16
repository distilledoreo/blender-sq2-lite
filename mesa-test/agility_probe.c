// Agility probe: exports D3D12SDKVersion/D3D12SDKPath so inbox D3D12.dll loads
// app-local D3D12/D3D12Core.dll, then creates a WGL context via beside-exe
// Mesa opengl32.dll and prints GL strings. No Blender needed.
#include <windows.h>
#include <stdio.h>

// Agility opt-in: must be exported from the MAIN exe.
__declspec(dllexport) extern const UINT D3D12SDKVersion = 619;
__declspec(dllexport) extern const char *D3D12SDKPath = ".\\D3D12\\";

static LRESULT CALLBACK WndProc(HWND h, UINT m, WPARAM w, LPARAM l) { return DefWindowProcW(h, m, w, l); }

int main(void) {
  HINSTANCE hi = GetModuleHandleW(NULL);
  WNDCLASSW wc = {0};
  wc.lpfnWndProc = WndProc; wc.hInstance = hi; wc.lpszClassName = L"AgilityProbe";
  if (!RegisterClassW(&wc)) { printf("RegisterClass failed %lu\n", GetLastError()); return 1; }
  HWND hwnd = CreateWindowExW(0, L"AgilityProbe", L"probe", 0, 0, 0, 64, 64, NULL, NULL, hi, NULL);
  if (!hwnd) { printf("CreateWindow failed %lu\n", GetLastError()); return 1; }
  HDC hdc = GetDC(hwnd);
  PIXELFORMATDESCRIPTOR pfd = {0};
  pfd.nSize = sizeof(pfd); pfd.nVersion = 1;
  pfd.dwFlags = PFD_DRAW_TO_WINDOW | PFD_SUPPORT_OPENGL | PFD_DOUBLEBUFFER;
  pfd.iPixelType = PFD_TYPE_RGBA; pfd.cColorBits = 24; pfd.cDepthBits = 24; pfd.cStencilBits = 8;
  int fmt = ChoosePixelFormat(hdc, &pfd);
  if (!fmt) { printf("ChoosePixelFormat failed %lu\n", GetLastError()); return 1; }
  if (!SetPixelFormat(hdc, fmt, &pfd)) { printf("SetPixelFormat failed %lu\n", GetLastError()); return 1; }
  HGLRC hgl = wglCreateContext(hdc);
  if (!hgl) { printf("wglCreateContext failed %lu\n", GetLastError()); return 1; }
  if (!wglMakeCurrent(hdc, hgl)) { printf("wglMakeCurrent failed %lu\n", GetLastError()); return 1; }
  const char *(*pGetString)(unsigned) = (const char *(*)(unsigned))wglGetProcAddress("glGetString");
  // glGetString is a 1.1 export; use static import as fallback
  HMODULE gl = GetModuleHandleW(L"opengl32.dll");
  if (!pGetString && gl) pGetString = (const char *(*)(unsigned))GetProcAddress(gl, "glGetString");
  const char *(*pGetStringi)(unsigned, unsigned) = (const char *(*)(unsigned, unsigned))wglGetProcAddress("glGetStringi");
  void (*pGetIntegerv)(unsigned, int *) = (void (*)(unsigned, int *))wglGetProcAddress("glGetIntegerv");
  if (pGetString) {
    printf("VENDOR=%s\n", pGetString(0x1F00));
    printf("RENDERER=%s\n", pGetString(0x1F01));
    printf("VERSION=%s\n", pGetString(0x1F02));
    printf("GLSL=%s\n", pGetString(0x8B8C));
  } else {
    printf("no glGetString\n"); return 1;
  }
  if (pGetIntegerv && pGetStringi) {
    int n = -1; pGetIntegerv(0x821D, &n);
    printf("NUM_EXT=%d\n", n);
    int show = n > 400 ? 400 : n;
    for (int i = 0; i < show; i++) {
      const char *e = pGetStringi(0x1F03, (unsigned)i);
      if (e) {
        // print only interesting ones to keep log short
        const char *s = e;
        if (strstr(s, "compute_shader") || strstr(s, "shader_image") || strstr(s, "clip_control") ||
            strstr(s, "draw_parameters") || strstr(s, "storage_buffer") || strstr(s, "multi_draw")) {
          printf("EXT* %s\n", s);
        }
      }
    }
    printf("EXT_DUMP_DONE n=%d\n", n);
  } else {
    printf("no glGetIntegerv/glGetStringi\n");
  }
  wglMakeCurrent(NULL, NULL); wglDeleteContext(hgl);
  return 0;
}
