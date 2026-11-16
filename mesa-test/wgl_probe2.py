import ctypes, sys
mesa_gl = sys.argv[1]
opengl32 = ctypes.WinDLL(mesa_gl)
user32 = ctypes.WinDLL("user32.dll")
gdi32 = ctypes.WinDLL("gdi32.dll")
opengl32.glGetString.argtypes=[ctypes.c_uint]; opengl32.glGetString.restype=ctypes.c_char_p
opengl32.glGetError.argtypes=[]; opengl32.glGetError.restype=ctypes.c_uint
WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_int64, ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint64, ctypes.c_int64)
def wndproc(h,m,w,l):
    return user32.DefWindowProcW(ctypes.c_void_p(h or 0), m, ctypes.c_void_p(w or 0), ctypes.c_void_p(l or 0))
class WNDCLASS(ctypes.Structure):
    _fields_=[("style",ctypes.c_uint),("lpfnWndProc",WNDPROC),("cbClsExtra",ctypes.c_int),("cbWndExtra",ctypes.c_int),("hInstance",ctypes.c_void_p),("hIcon",ctypes.c_void_p),("hCursor",ctypes.c_void_p),("hbrBackground",ctypes.c_void_p),("lpszMenuName",ctypes.c_wchar_p),("lpszClassName",ctypes.c_wchar_p)]
wc = WNDCLASS(0, WNDPROC(wndproc), 0, 0, None, None, None, None, None, "MesaProbeSQ2b")
user32.RegisterClassW(ctypes.byref(wc))
hwnd = user32.CreateWindowExW(0, "MesaProbeSQ2b", "probe", 0, 0,0,64,64, None, None, None, None)
hdc = user32.GetDC(hwnd)
print("hwnd/hdc:", hwnd, hdc)
class PFD(ctypes.Structure):
    _fields_=[("nSize",ctypes.c_ushort),("nVersion",ctypes.c_ushort),("dwFlags",ctypes.c_ulong),("iPixelType",ctypes.c_ubyte),("cColorBits",ctypes.c_ubyte),("cRedBits",ctypes.c_ubyte),("cRedShift",ctypes.c_ubyte),("cGreenBits",ctypes.c_ubyte),("cGreenShift",ctypes.c_ubyte),("cBlueBits",ctypes.c_ubyte),("cBlueShift",ctypes.c_ubyte),("cAlphaBits",ctypes.c_ubyte),("cAlphaShift",ctypes.c_ubyte),("cAccumBits",ctypes.c_ubyte),("cAccumRedBits",ctypes.c_ubyte),("cAccumGreenBits",ctypes.c_ubyte),("cAccumBlueBits",ctypes.c_ubyte),("cAccumAlphaBits",ctypes.c_ubyte),("cDepthBits",ctypes.c_ubyte),("cStencilBits",ctypes.c_ubyte),("cAuxBuffers",ctypes.c_ubyte),("iLayerType",ctypes.c_ubyte),("bReserved",ctypes.c_ubyte),("dwLayerMask",ctypes.c_ulong),("dwVisibleMask",ctypes.c_ulong),("dwDamageMask",ctypes.c_ulong)]
pfd = PFD()
pfd.nSize = ctypes.sizeof(PFD); pfd.nVersion=1
pfd.dwFlags=0x4|0x20|0x1; pfd.iPixelType=0; pfd.cColorBits=24; pfd.cDepthBits=24; pfd.cStencilBits=8; pfd.iLayerType=0
fmt = gdi32.ChoosePixelFormat(hdc, ctypes.byref(pfd))
print("pfmt:", fmt)
print("setpf:", gdi32.SetPixelFormat(hdc, fmt, ctypes.byref(pfd)))
opengl32.wglCreateContext.argtypes=[ctypes.c_void_p]; opengl32.wglCreateContext.restype=ctypes.c_void_p
opengl32.wglMakeCurrent.argtypes=[ctypes.c_void_p,ctypes.c_void_p]; opengl32.wglMakeCurrent.restype=ctypes.c_int
hgl = opengl32.wglCreateContext(ctypes.c_void_p(hdc))
print("hgl:", hgl)
print("make:", opengl32.wglMakeCurrent(ctypes.c_void_p(hdc), ctypes.c_void_p(hgl)))
for tag,name in [(0x1F00,"VERSION"),(0x1F01,"RENDERER"),(0x1F02,"VENDOR"),(0x8B8C,"GLSL")]:
    v = opengl32.glGetString(tag)
    print(name,"=", v.decode() if v else f"<NULL> err={hex(opengl32.glGetError())}")
# num extensions + dump
opengl32.wglGetProcAddress.argtypes=[ctypes.c_char_p]; opengl32.wglGetProcAddress.restype=ctypes.c_void_p
addr = opengl32.wglGetProcAddress(b"glGetStringi")
print("glGetStringi:", addr)
if addr:
    FN = ctypes.WINFUNCTYPE(ctypes.c_char_p, ctypes.c_uint, ctypes.c_uint)(addr)
    opengl32.glGetIntegerv.argtypes=[ctypes.c_uint, ctypes.POINTER(ctypes.c_int)]
    n=ctypes.c_int(); opengl32.glGetIntegerv(0x1F03, ctypes.byref(n))
    print("NUM_EXT:", n.value, "err:", hex(opengl32.glGetError()))
    exts=[]
    for i in range(n.value):
        s=FN(0x1F03, i)
        if s: exts.append(s.decode())
    open(sys.argv[2],"w").write("\n".join(exts))
    print("wrote", sys.argv[2], len(exts))
    for e in exts:
        if any(k in e for k in ["draw_parameters","clip_control","shader_image","storage","compute_shader","multi_draw"]):
            print(" *", e)
