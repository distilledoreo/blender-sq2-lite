import ctypes, sys, os
mesa_gl, ext_out = sys.argv[1], sys.argv[2]
use_agility = len(sys.argv) > 3 and sys.argv[3] == "agility"
# Optional Agility opt-in via D3D12GetInterface + ID3D12SDKConfiguration::SetSDKVersion (no exe exports needed)
if use_agility:
    d3d12 = ctypes.WinDLL("d3d12.dll")
    # CLSID_D3D12SDKConfiguration {7cda6aca-a03e-49c8-9456-939d4403c7cf}, IID ID3D12SDKConfiguration {e9eb5314-33aa-42b2-a718-f12872877c77}
    class GUID(ctypes.Structure):
        _fields_=[("D1",ctypes.c_ulong),("D2",ctypes.c_ushort),("D3",ctypes.c_ushort),("D4",ctypes.c_ubyte*8)]
    def G(s):
        a,b,c,d,e = s.split("-")
        return GUID(int(a,16),int(b,16),int(c,16),(ctypes.c_ubyte*8)(int(d[:2],16),int(d[2:],16),*[int(e[i:i+2],16) for i in range(0,12,2)]))
    CLSID = G("7cda6aca-a03e-49c8-9456-939d4403c7cf")
    IID = G("e9eb5314-33aa-42b2-a718-f12872877c77")
    d3d12.D3D12GetInterface.argtypes=[ctypes.POINTER(GUID),ctypes.POINTER(GUID),ctypes.POINTER(ctypes.c_void_p)]; d3d12.D3D12GetInterface.restype=ctypes.c_long
    cfg = ctypes.c_void_p()
    hr = d3d12.D3D12GetInterface(ctypes.byref(CLSID), ctypes.byref(IID), ctypes.byref(cfg))
    print(f"D3D12GetInterface: hr=0x{hr&0xFFFFFFFF:08x} cfg={hex(cfg.value or 0)}")
    if hr >= 0 and cfg.value:
        vt = ctypes.cast(cfg.value, ctypes.POINTER(ctypes.c_void_p))
        # ID3D12SDKConfiguration vtable: IUnknown(0-2), SetSDKVersion(3)
        import ctypes as C
        FN = C.WINFUNCTYPE(C.c_long, C.c_void_p, C.c_uint, C.c_char_p)
        setver = FN(C.cast(vt[3], C.c_void_p).value)
        hr2 = setver(cfg.value, 619, b".\D3D12\\")
        print(f"SetSDKVersion(619,'.\D3D12\'): hr=0x{hr2&0xFFFFFFFF:08x}")
        print("cwd:", os.getcwd(), "exe:", sys.executable)
opengl32 = ctypes.WinDLL(mesa_gl)
user32 = ctypes.WinDLL("user32.dll"); gdi32 = ctypes.WinDLL("gdi32.dll")
opengl32.wglGetProcAddress.argtypes=[ctypes.c_char_p]; opengl32.wglGetProcAddress.restype=ctypes.c_void_p
WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_int64, ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint64, ctypes.c_int64)
def wndproc(h,m,w,l): return user32.DefWindowProcW(ctypes.c_void_p(h or 0), m, ctypes.c_void_p(w or 0), ctypes.c_void_p(l or 0))
class WC(ctypes.Structure):
    _fields_=[("s",ctypes.c_uint),("p",WNDPROC),("a",ctypes.c_int),("b",ctypes.c_int),("c",ctypes.c_void_p),("d",ctypes.c_void_p),("e",ctypes.c_void_p),("f",ctypes.c_void_p),("g",ctypes.c_wchar_p),("h",ctypes.c_wchar_p)]
wc = WC(0, WNDPROC(wndproc), 0,0,None,None,None,None,None,"MesaProbeSQ2c")
user32.RegisterClassW(ctypes.byref(wc))
hwnd = user32.CreateWindowExW(0,"MesaProbeSQ2c","p",0,0,0,64,64,None,None,None,None)
hdc = user32.GetDC(hwnd)
class PFD(ctypes.Structure):
    _fields_=[("nSize",ctypes.c_ushort),("nVersion",ctypes.c_ushort),("dwFlags",ctypes.c_ulong),("iPixelType",ctypes.c_ubyte),("cColorBits",ctypes.c_ubyte),("cRedBits",ctypes.c_ubyte),("cRedShift",ctypes.c_ubyte),("cGreenBits",ctypes.c_ubyte),("cGreenShift",ctypes.c_ubyte),("cBlueBits",ctypes.c_ubyte),("cBlueShift",ctypes.c_ubyte),("cAlphaBits",ctypes.c_ubyte),("cAlphaShift",ctypes.c_ubyte),("cAccumBits",ctypes.c_ubyte),("cAccumRedBits",ctypes.c_ubyte),("cAccumGreenBits",ctypes.c_ubyte),("cAccumBlueBits",ctypes.c_ubyte),("cAccumAlphaBits",ctypes.c_ubyte),("cDepthBits",ctypes.c_ubyte),("cStencilBits",ctypes.c_ubyte),("cAuxBuffers",ctypes.c_ubyte),("iLayerType",ctypes.c_ubyte),("bReserved",ctypes.c_ubyte),("dwLayerMask",ctypes.c_ulong),("dwVisibleMask",ctypes.c_ulong),("dwDamageMask",ctypes.c_ulong)]
pfd=PFD(); pfd.nSize=ctypes.sizeof(PFD); pfd.nVersion=1; pfd.dwFlags=0x25; pfd.cColorBits=24; pfd.cDepthBits=24; pfd.cStencilBits=8
fmt=gdi32.ChoosePixelFormat(hdc,ctypes.byref(pfd)); gdi32.SetPixelFormat(hdc,fmt,ctypes.byref(pfd))
opengl32.wglCreateContext.argtypes=[ctypes.c_void_p]; opengl32.wglCreateContext.restype=ctypes.c_void_p
opengl32.wglMakeCurrent.argtypes=[ctypes.c_void_p,ctypes.c_void_p]; opengl32.wglMakeCurrent.restype=ctypes.c_int
hgl=opengl32.wglCreateContext(ctypes.c_void_p(hdc)); opengl32.wglMakeCurrent(ctypes.c_void_p(hdc),ctypes.c_void_p(hgl))
print("ctx:",hgl)
# glGetString via direct export (1.1 entry points): VENDOR=0x1F00 RENDERER=0x1F01 VERSION=0x1F02 GLSL=0x8B8C
opengl32.glGetString.argtypes=[ctypes.c_uint]; opengl32.glGetString.restype=ctypes.c_char_p
opengl32.glGetError.argtypes=[]; opengl32.glGetError.restype=ctypes.c_uint
for tag,name in [(0x1F00,"VENDOR"),(0x1F01,"RENDERER"),(0x1F02,"VERSION"),(0x8B8C,"GLSL")]:
    v=opengl32.glGetString(tag); print(name,"=",v.decode() if v else f"<NULL> {hex(opengl32.glGetError())}")
# GL>1.1 via proc addresses: glGetIntegerv + glGetStringi
FN_I = ctypes.WINFUNCTYPE(None, ctypes.c_uint, ctypes.POINTER(ctypes.c_int))
FN_S = ctypes.WINFUNCTYPE(ctypes.c_char_p, ctypes.c_uint, ctypes.c_uint)
pI = opengl32.wglGetProcAddress(b"glGetIntegerv"); pS = opengl32.wglGetProcAddress(b"glGetStringi")
print("proc glGetIntegerv:",pI,"glGetStringi:",pS)
exts=[]
if pI and pS:
    gi = FN_I(pI); gs = FN_S(pS)
    n=ctypes.c_int(-1); gi(0x821D, ctypes.byref(n))  # GL_NUM_EXTENSIONS
    print("NUM_EXT:",n.value)
    for i in range(max(0,n.value)):
        s=gs(0x1F03,i)
        if s: exts.append(s.decode())
    print("EXT_COUNT:",len(exts))
    open(ext_out,"w").write("\n".join(exts))
    keys=["draw_parameters","clip_control","shader_image","shader_storage","compute_shader","multi_draw","texture_filter_anisotropic","tessellation","ssbo","image_load_store","GL_ARB_framebuffer"]
    for e in exts:
        el=e.lower()
        if any(k in el for k in keys): print(" *",e)
else: print("no proc addrs")
