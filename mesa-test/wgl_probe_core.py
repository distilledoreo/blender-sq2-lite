import ctypes, sys
mesa_gl, ext_out = sys.argv[1], sys.argv[2]
opengl32 = ctypes.WinDLL(mesa_gl)
user32 = ctypes.WinDLL("user32.dll"); gdi32 = ctypes.WinDLL("gdi32.dll")
opengl32.wglGetProcAddress.argtypes=[ctypes.c_char_p]; opengl32.wglGetProcAddress.restype=ctypes.c_void_p
opengl32.wglCreateContext.argtypes=[ctypes.c_void_p]; opengl32.wglCreateContext.restype=ctypes.c_void_p
opengl32.wglMakeCurrent.argtypes=[ctypes.c_void_p,ctypes.c_void_p]; opengl32.wglMakeCurrent.restype=ctypes.c_int
opengl32.wglDeleteContext.argtypes=[ctypes.c_void_p]; opengl32.wglDeleteContext.restype=ctypes.c_int
WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_int64, ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint64, ctypes.c_int64)
def wndproc(h,m,w,l): return user32.DefWindowProcW(ctypes.c_void_p(h or 0), m, ctypes.c_void_p(w or 0), ctypes.c_void_p(l or 0))
class WC(ctypes.Structure):
    _fields_=[("s",ctypes.c_uint),("p",WNDPROC),("a",ctypes.c_int),("b",ctypes.c_int),("c",ctypes.c_void_p),("d",ctypes.c_void_p),("e",ctypes.c_void_p),("f",ctypes.c_void_p),("g",ctypes.c_wchar_p),("h",ctypes.c_wchar_p)]
wc = WC(0, WNDPROC(wndproc), 0,0,None,None,None,None,None,"MesaProbeCore")
user32.RegisterClassW(ctypes.byref(wc))
hwnd = user32.CreateWindowExW(0,"MesaProbeCore","p",0,0,0,64,64,None,None,None,None)
hdc = user32.GetDC(hwnd)
class PFD(ctypes.Structure):
    _fields_=[("nSize",ctypes.c_ushort),("nVersion",ctypes.c_ushort),("dwFlags",ctypes.c_ulong),("iPixelType",ctypes.c_ubyte),("cColorBits",ctypes.c_ubyte),("cRedBits",ctypes.c_ubyte),("cRedShift",ctypes.c_ubyte),("cGreenBits",ctypes.c_ubyte),("cGreenShift",ctypes.c_ubyte),("cBlueBits",ctypes.c_ubyte),("cBlueShift",ctypes.c_ubyte),("cAlphaBits",ctypes.c_ubyte),("cAlphaShift",ctypes.c_ubyte),("cAccumBits",ctypes.c_ubyte),("cAccumRedBits",ctypes.c_ubyte),("cAccumGreenBits",ctypes.c_ubyte),("cAccumBlueBits",ctypes.c_ubyte),("cAccumAlphaBits",ctypes.c_ubyte),("cDepthBits",ctypes.c_ubyte),("cStencilBits",ctypes.c_ubyte),("cAuxBuffers",ctypes.c_ubyte),("iLayerType",ctypes.c_ubyte),("bReserved",ctypes.c_ubyte),("dwLayerMask",ctypes.c_ulong),("dwVisibleMask",ctypes.c_ulong),("dwDamageMask",ctypes.c_ulong)]
pfd=PFD(); pfd.nSize=ctypes.sizeof(PFD); pfd.nVersion=1; pfd.dwFlags=0x25; pfd.cColorBits=24; pfd.cDepthBits=24; pfd.cStencilBits=8
fmt=gdi32.ChoosePixelFormat(hdc,ctypes.byref(pfd)); gdi32.SetPixelFormat(hdc,fmt,ctypes.byref(pfd))
# temp context to get wglCreateContextAttribsARB
tmp=opengl32.wglCreateContext(ctypes.c_void_p(hdc)); opengl32.wglMakeCurrent(ctypes.c_void_p(hdc),ctypes.c_void_p(tmp))
pAttr=opengl32.wglGetProcAddress(b"wglCreateContextAttribsARB")
print("wglCreateContextAttribsARB:",pAttr)
hgl=None
if pAttr:
    FN=ctypes.WINFUNCTYPE(ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.POINTER(ctypes.c_int))(pAttr)
    WGL_CONTEXT_MAJOR_VERSION_ARB=0x2091; WGL_CONTEXT_MINOR_VERSION_ARB=0x2092; WGL_CONTEXT_PROFILE_MASK_ARB=0x9126; WGL_CONTEXT_CORE_PROFILE_BIT_ARB=0x1
    for maj,minor in [(4,3),(4,1),(3,3)]:
        attribs=(ctypes.c_int*7)(WGL_CONTEXT_MAJOR_VERSION_ARB,maj,WGL_CONTEXT_MINOR_VERSION_ARB,minor,WGL_CONTEXT_PROFILE_MASK_ARB,WGL_CONTEXT_CORE_PROFILE_BIT_ARB,0)
        h=FN(ctypes.c_void_p(hdc),None,attribs)
        print(f"core {maj}.{minor}: {h}")
        if h: hgl=h; break
opengl32.wglMakeCurrent(None,None); opengl32.wglDeleteContext(ctypes.c_void_p(tmp))
if not hgl: print("NO_CORE_CONTEXT"); sys.exit(2)
print("make:",opengl32.wglMakeCurrent(ctypes.c_void_p(hdc),ctypes.c_void_p(hgl)))
opengl32.glGetString.argtypes=[ctypes.c_uint]; opengl32.glGetString.restype=ctypes.c_char_p
for tag,name in [(0x1F00,"VENDOR"),(0x1F01,"RENDERER"),(0x1F02,"VERSION"),(0x8B8C,"GLSL")]:
    v=opengl32.glGetString(tag); print(name,"=",v.decode() if v else "<NULL>")
FN_I=ctypes.WINFUNCTYPE(None,ctypes.c_uint,ctypes.POINTER(ctypes.c_int))(opengl32.wglGetProcAddress(b"glGetIntegerv"))
FN_S=ctypes.WINFUNCTYPE(ctypes.c_char_p,ctypes.c_uint,ctypes.c_uint)(opengl32.wglGetProcAddress(b"glGetStringi"))
n=ctypes.c_int(-1); FN_I(0x821D,ctypes.byref(n)); print("NUM_EXT:",n.value)
exts=[]
for i in range(max(0,n.value)):
    s=FN_S(0x1F03,i)
    if s: exts.append(s.decode())
open(ext_out,"w").write("\n".join(exts)); print("EXT_COUNT:",len(exts))
for e in exts:
    if any(k in e.lower() for k in ["compute_shader","shader_image_load_store","shader_storage","draw_parameters","clip_control"]): print(" *",e)
