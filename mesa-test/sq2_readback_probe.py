import ctypes, sys, os

# Plain buffer read-back probe for the SQ2 Adreno + Mesa d3d12 path.
# Based on the working wgl_probe_core.py harness (same WGL core-context setup).
# No compute, no draw: glBufferData(16) then glGetBufferSubData, plus map-read.

mesa_gl = sys.argv[1]
opengl32 = ctypes.WinDLL(mesa_gl)
user32 = ctypes.WinDLL("user32.dll")
gdi32 = ctypes.WinDLL("gdi32.dll")

opengl32.wglGetProcAddress.argtypes = [ctypes.c_char_p]
opengl32.wglGetProcAddress.restype = ctypes.c_void_p
opengl32.wglCreateContext.argtypes = [ctypes.c_void_p]
opengl32.wglCreateContext.restype = ctypes.c_void_p
opengl32.wglMakeCurrent.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
opengl32.wglMakeCurrent.restype = ctypes.c_int
opengl32.wglDeleteContext.argtypes = [ctypes.c_void_p]
opengl32.wglDeleteContext.restype = ctypes.c_int

WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_int64, ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint64, ctypes.c_int64)


def wndproc(h, m, w, l):
    return user32.DefWindowProcW(ctypes.c_void_p(h or 0), m, ctypes.c_void_p(w or 0), ctypes.c_void_p(l or 0))


class WC(ctypes.Structure):
    _fields_ = [("s", ctypes.c_uint), ("p", WNDPROC), ("a", ctypes.c_int), ("b", ctypes.c_int),
                ("c", ctypes.c_void_p), ("d", ctypes.c_void_p), ("e", ctypes.c_void_p),
                ("f", ctypes.c_void_p), ("g", ctypes.c_wchar_p), ("h", ctypes.c_wchar_p)]


wc = WC(0, WNDPROC(wndproc), 0, 0, None, None, None, None, None, "MesaReadbackProbe")
user32.RegisterClassW(ctypes.byref(wc))
hwnd = user32.CreateWindowExW(0, "MesaReadbackProbe", "p", 0, 0, 0, 64, 64, None, None, None, None)
hdc = user32.GetDC(hwnd)


class PFD(ctypes.Structure):
    _fields_ = [("nSize", ctypes.c_ushort), ("nVersion", ctypes.c_ushort), ("dwFlags", ctypes.c_ulong),
                ("iPixelType", ctypes.c_ubyte), ("cColorBits", ctypes.c_ubyte), ("cRedBits", ctypes.c_ubyte),
                ("cRedShift", ctypes.c_ubyte), ("cGreenBits", ctypes.c_ubyte), ("cGreenShift", ctypes.c_ubyte),
                ("cBlueBits", ctypes.c_ubyte), ("cBlueShift", ctypes.c_ubyte), ("cAlphaBits", ctypes.c_ubyte),
                ("cAlphaShift", ctypes.c_ubyte), ("cAccumBits", ctypes.c_ubyte), ("cAccumRedBits", ctypes.c_ubyte),
                ("cAccumGreenBits", ctypes.c_ubyte), ("cAccumBlueBits", ctypes.c_ubyte),
                ("cAccumAlphaBits", ctypes.c_ubyte), ("cDepthBits", ctypes.c_ubyte),
                ("cStencilBits", ctypes.c_ubyte), ("cAuxBuffers", ctypes.c_ubyte),
                ("iLayerType", ctypes.c_ubyte), ("bReserved", ctypes.c_ubyte), ("dwLayerMask", ctypes.c_ulong),
                ("dwVisibleMask", ctypes.c_ulong), ("dwDamageMask", ctypes.c_ulong)]


pfd = PFD()
pfd.nSize = ctypes.sizeof(PFD)
pfd.nVersion = 1
pfd.dwFlags = 0x25
pfd.cColorBits = 24
pfd.cDepthBits = 24
pfd.cStencilBits = 8
fmt = gdi32.ChoosePixelFormat(hdc, ctypes.byref(pfd))
gdi32.SetPixelFormat(hdc, fmt, ctypes.byref(pfd))

tmp = opengl32.wglCreateContext(ctypes.c_void_p(hdc))
opengl32.wglMakeCurrent(ctypes.c_void_p(hdc), ctypes.c_void_p(tmp))
pAttr = opengl32.wglGetProcAddress(b"wglCreateContextAttribsARB")
hgl = None
if pAttr:
    FN = ctypes.WINFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_int))(pAttr)
    MAJ, MIN, PMASK, CORE = 0x2091, 0x2092, 0x9126, 0x1
    for maj, minor in [(4, 3), (4, 1), (3, 3)]:
        attribs = (ctypes.c_int * 7)(MAJ, maj, MIN, minor, PMASK, CORE, 0)
        h = FN(ctypes.c_void_p(hdc), None, attribs)
        print("core %d.%d ctx: %s" % (maj, minor, h))
        if h:
            hgl = h
            break
opengl32.wglMakeCurrent(None, None)
opengl32.wglDeleteContext(ctypes.c_void_p(tmp))
if not hgl:
    print("NO_CORE_CONTEXT")
    sys.exit(2)
if not opengl32.wglMakeCurrent(ctypes.c_void_p(hdc), ctypes.c_void_p(hgl)):
    print("MAKE_CURRENT_FAILED")
    sys.exit(3)

opengl32.glGetString.argtypes = [ctypes.c_uint]
opengl32.glGetString.restype = ctypes.c_char_p
for tag, name in [(0x1F00, "VENDOR"), (0x1F01, "RENDERER"), (0x1F02, "VERSION"), (0x8B8C, "GLSL")]:
    v = opengl32.glGetString(tag)
    print("%s = %s" % (name, v.decode() if v else "<NULL>"))


def proc(name):
    p = opengl32.wglGetProcAddress(name.encode())
    if not p:
        raise RuntimeError("missing " + name)
    return p


glGetError = ctypes.WINFUNCTYPE(ctypes.c_uint)(proc("glGetError"))
glGenBuffers = ctypes.WINFUNCTYPE(None, ctypes.c_int, ctypes.POINTER(ctypes.c_uint))(proc("glGenBuffers"))
glBindBuffer = ctypes.WINFUNCTYPE(None, ctypes.c_uint, ctypes.c_uint)(proc("glBindBuffer"))
glBufferData = ctypes.WINFUNCTYPE(None, ctypes.c_uint, ctypes.c_ssize_t, ctypes.c_void_p, ctypes.c_uint)(proc("glBufferData"))
glGetBufferSubData = ctypes.WINFUNCTYPE(None, ctypes.c_uint, ctypes.c_ssize_t, ctypes.c_ssize_t, ctypes.c_void_p)(proc("glGetBufferSubData"))
glBufferSubData = ctypes.WINFUNCTYPE(None, ctypes.c_uint, ctypes.c_ssize_t, ctypes.c_ssize_t, ctypes.c_void_p)(proc("glBufferSubData"))
glMapBufferRange = ctypes.WINFUNCTYPE(ctypes.c_void_p, ctypes.c_uint, ctypes.c_ssize_t, ctypes.c_ssize_t, ctypes.c_uint)(proc("glMapBufferRange"))
glUnmapBuffer = ctypes.WINFUNCTYPE(ctypes.c_ubyte, ctypes.c_uint)(proc("glUnmapBuffer"))
glFinish = ctypes.WINFUNCTYPE(None)(proc("glFinish"))

GL_ARRAY_BUFFER = 0x8892
GL_UNIFORM_BUFFER = 0x8A11
GL_STATIC_DRAW = 0x88E4
GL_MAP_READ_BIT = 0x1

while glGetError() != 0:
    pass


def err(tag):
    e = glGetError()
    print("  glGetError(%s) = 0x%x" % (tag, e))
    return e


pattern = bytes(range(16))
src = ctypes.create_string_buffer(pattern, 16)


def dump(buf, n=16):
    return " ".join("%02x" % b for b in bytes(buf[:n]))


fails = 0
for target, tname in [(GL_ARRAY_BUFFER, "ARRAY_BUFFER"), (GL_UNIFORM_BUFFER, "UNIFORM_BUFFER")]:
    ids = (ctypes.c_uint * 1)()
    glGenBuffers(1, ids)
    glBindBuffer(target, ids[0])
    err("bind %s" % tname)
    glBufferData(target, 16, ctypes.cast(src, ctypes.c_void_p), GL_STATIC_DRAW)
    if err("bufferdata %s" % tname):
        fails += 1
        continue
    glFinish()
    for attempt in range(3):
        dst = ctypes.create_string_buffer(16)
        glGetBufferSubData(target, 0, 16, ctypes.cast(dst, ctypes.c_void_p))
        e = err("getbuffersubdata %s #%d" % (tname, attempt + 1))
        got = bytes(dst[:16])
        ok = got == pattern
        if e or not ok:
            fails += 1
        print("  %s read #%d match=%s got=[%s]" % (tname, attempt + 1, ok, dump(dst)))
    glBufferSubData(target, 0, 16, ctypes.cast(src, ctypes.c_void_p))
    if err("buffersubdata %s" % tname):
        fails += 1
    dst = ctypes.create_string_buffer(16)
    glGetBufferSubData(target, 0, 16, ctypes.cast(dst, ctypes.c_void_p))
    e = err("getbuffersubdata-after-subdata %s" % tname)
    print("  %s read-after-write match=%s what=[%s]" % (tname, bytes(dst[:16]) == pattern, dump(dst)))
    if e or bytes(dst[:16]) != pattern:
        fails += 1
    ptr = glMapBufferRange(target, 0, 16, GL_MAP_READ_BIT)
    if not ptr:
        print("  MAP_FAILED %s" % tname)
        fails += 1
        err("map %s" % tname)
    else:
        got = ctypes.string_at(ptr, 16)
        glUnmapBuffer(target)
        e = err("unmap %s" % tname)
        print("  %s map-read match=%s what=[%s]" % (tname, got == pattern, " ".join("%02x" % b for b in got)))
        if e or got != pattern:
            fails += 1
    glBindBuffer(target, 0)

print("RESULT: %s (fails=%d)" % ("PASS" if fails == 0 else "FAIL", fails))
sys.exit(0 if fails == 0 else 1)
