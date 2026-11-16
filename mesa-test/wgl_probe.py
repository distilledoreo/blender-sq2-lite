import ctypes, sys
mesa_gl = sys.argv[1]
print("MESA:", mesa_gl)
opengl32 = ctypes.WinDLL(mesa_gl)
user32 = ctypes.WinDLL("user32.dll")
gdi32 = ctypes.WinDLL("gdi32.dll")
# wgl prototypes
opengl32.wglGetProcAddress.argtypes=[ctypes.c_char_p]; opengl32.wglGetProcAddress.restype=ctypes.c_void_p
opengl32.glGetString.argtypes=[ctypes.c_uint]; opengl32.glGetString.restype=ctypes.c_char_p
opengl32.glGetIntegerv.argtypes=[ctypes.c_uint, ctypes.POINTER(ctypes.c_int)]; opengl32.glGetIntegerv.restype=None
opengl32.glGetError.argtypes=[]; opengl32.glGetError.restype=ctypes.c_uint
# Create dummy window
WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p)
class WNDCLASS(ctypes.Structure):
    _fields_=[("style",ctypes.c_uint),("lpfnWndProc",WNDPROC),("cbClsExtra",ctypes.c_int),("cbWndExtra",ctypes.c_int),("hInstance",ctypes.c_void_p),("hIcon",ctypes.c_void_p),("hCursor",ctypes.c_void_p),("hbrBackground",ctypes.c_void_p),("lpszMenuName",ctypes.c_wchar_p),("lpszClassName",ctypes.c_wchar_p)]
def wndproc(h,m,w,l): return user32.DefWindowProcW(h,m,w,l)
wc = WNDCLASS(0, WNDPROC(wndproc), 0, 0, None, None, None, None, None, "MesaProbeSQ2")
user32.RegisterClassW(ctypes.byref(wc))
hwnd = user32.CreateWindowExW(0, "MesaProbeSQ2", "probe", 0, 0,0,64,64, None, None, None, None)
print("hwnd:", hex(hwnd or 0))
hdc = user32.GetDC(hwnd)
print("hdc:", hex(hdc or 0))
class PIXELFORMATDESCRIPTOR(ctypes.Structure):
    _fields_=[("nSize",ctypes.c_ushort),("nVersion",ctypes.c_ushort),("dwFlags",ctypes.c_ulong),("iPixelType",ctypes.c_ubyte),("cColorBits",ctypes.c_ubyte),("cRedBits",ctypes.c_ubyte),("cRedShift",ctypes.c_ubyte),("cGreenBits",ctypes.c_ubyte),("cGreenShift",ctypes.c_ubyte),("cBlueBits",ctypes.c_ubyte),("cBlueShift",ctypes.c_ubyte),("cAlphaBits",ctypes.c_ubyte),("cAlphaShift",ctypes.c_ubyte),("cAccumBits",ctypes.c_ubyte),("cAccumRedBits",ctypes.c_ubyte),("cAccumGreenBits",ctypes.c_ubyte),("cAccumBlueBits",ctypes.c_ubyte),("cAccumAlphaBits",ctypes.c_ubyte),("cDepthBits",ctypes.c_ubyte),("cStencilBits",ctypes.c_ubyte),("cAuxBuffers",ctypes.c_ubyte),("iLayerType",ctypes.c_ubyte),("bReserved",ctypes.c_ubyte),("dwLayerMask",ctypes.c_ulong),("dwVisibleMask",ctypes.c_ulong),("dwDamageMask",ctypes.c_ulong)]
PFD_DRAW_TO_WINDOW=0x4; PFD_SUPPORT_OPENGL=0x20; PFD_DOUBLEBUFFER=0x1; PFD_TYPE_RGBA=0
pfd = PIXELFORMATDESCRIPTOR(ctypes.sizeof(PIXELFORMATDESCRIPTOR),1,PFD_DRAW_TO_WINDOW|PFD_SUPPORT_OPENGL|PFD_DOUBLEBUFFER,PFD_TYPE_RGBA,24,0,0,0,0,0,0,0,0,0,0,0,0,0,0,24,8,0,0,0,0,0,0)
fmt = gdi32.ChoosePixelFormat(hdc, ctypes.byref(pfd))
print("pfmt:", fmt)
gdi32.SetPixelFormat(hdc, fmt, ctypes.byref(pfd))
opengl32.wglCreateContext.argtypes=[ctypes.c_void_p]; opengl32.wglCreateContext.restype=ctypes.c_void_p
opengl32.wglMakeCurrent.argtypes=[ctypes.c_void_p,ctypes.c_void_p]; opengl32.wglMakeCurrent.restype=ctypes.c_int
opengl32.wglGetCurrentContext.argtypes=[]; opengl32.wglGetCurrentContext.restype=ctypes.c_void_p
hgl = opengl32.wglCreateContext(hdc)
print("hgl:", hex(hgl or 0))
print("make:", opengl32.wglMakeCurrent(hdc, hgl), "cur:", hex(opengl32.wglGetCurrentContext() or 0))
for tag,name in [(0x1F00,"VERSION"),(0x1F01,"RENDERER"),(0x1F02,"VENDOR"),(0x8B8C,"GLSL")]:
    v = opengl32.glGetString(tag)
    print(name,"=", v.decode() if v else f"<NULL> glerr={hex(opengl32.glGetError())}")
# extensions: glGetStringi
try:
    opengl32.wglGetProcAddress.restype=ctypes.c_void_p
    addr = opengl32.wglGetProcAddress(b"glGetStringi")
    print("glGetStringi addr:", hex(addr or 0))
    if addr:
        FN = ctypes.WINFUNCTYPE(ctypes.c_char_p, ctypes.c_uint, ctypes.c_uint)(addr)
        n=ctypes.c_int(); opengl32.glGetIntegerv(0x1F03, ctypes.byref(n))  # GL_NUM_EXTENSIONS
        print("NUM_EXT:", n.value, "glerr:", hex(opengl32.glGetError()))
        exts=[]
        for i in range(min(n.value, 300)):
            s=FN(0x1F03, i)
            exts.append(s.decode() if s else "?")
        print("EXT_COUNT:", len(exts))
        open(sys.argv[2],"w").write("\n".join(exts))
        print("wrote", sys.argv[2])
        # print interesting ones
        for e in exts:
            if any(k in e for k in ["draw_parameters","clip_control","image_load","shader_image","SSBO","shader_storage","compute_shader","multi_draw_indirect"]):
                print("  *", e)
except Exception as e:
    print("ext fail:", e)
