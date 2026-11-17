"""Validated minimal compute test (no Blender): 4.2 core ctx, THREE SSBOs
(mirrors Blender end_sync which binds three SSBOs before GPU_compute_dispatch),
1x1x1 dispatch, glFinish, readback + compare.

Fixes vs compute_min.py (per assessment):
- Every GL entry point declares explicit argtypes + restype with 64-bit-safe
  types (GLsizeiptr/GLintptr as ssize_t, pointers as c_void_p). No implicit
  ctypes int conversion that truncates pointers/sizes on ARM64.
- glGetError checked after EVERY call; abort island records step.
- GL_BUFFER_SIZE read back for each buffer before dispatch (zero-size or
  failed buffer would become a null resource in Mesa).
- Three SSBOs bound to 0,1,2; shader touches all three.
"""
import ctypes
import faulthandler
import os
import sys

faulthandler.enable()

mesa_gl = sys.argv[1]
opengl32 = ctypes.WinDLL(mesa_gl)
user32 = ctypes.WinDLL("user32.dll")
gdi32 = ctypes.WinDLL("gdi32.dll")

opengl32.wglGetProcAddress.argtypes = [ctypes.c_char_p]
opengl32.wglGetProcAddress.restype = ctypes.c_void_p
opengl32.wglCreateContext.argtypes = [ctypes.c_void_p]
opengl32.wglCreateContext.restype = ctypes.c_void_p
opengl32.wglDeleteContext.argtypes = [ctypes.c_void_p]
opengl32.wglDeleteContext.restype = ctypes.c_int
opengl32.wglMakeCurrent.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
opengl32.wglMakeCurrent.restype = ctypes.c_int

errors = []

GLuint = ctypes.c_uint
GLenum = ctypes.c_uint
GLint = ctypes.c_int
GLsizei = ctypes.c_int
GLsizeiptr = ctypes.c_ssize_t
GLintptr = ctypes.c_ssize_t
GLboolean = ctypes.c_ubyte
GLuint64 = ctypes.c_uint64

WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_int64, ctypes.c_void_p,
                             ctypes.c_uint, ctypes.c_uint64, ctypes.c_int64)


def _wndproc(h, m, w, l):
    return user32.DefWindowProcW(ctypes.c_void_p(h or 0), m,
                                 ctypes.c_void_p(w or 0), ctypes.c_void_p(l or 0))


class WC(ctypes.Structure):
    _fields_ = [("s", ctypes.c_uint), ("p", WNDPROC), ("a", ctypes.c_int),
                ("b", ctypes.c_int), ("c", ctypes.c_void_p),
                ("d", ctypes.c_void_p), ("e", ctypes.c_void_p),
                ("f", ctypes.c_void_p), ("g", ctypes.c_wchar_p),
                ("h", ctypes.c_wchar_p)]


_wndproc_cb = WNDPROC(_wndproc)
wc = WC(0, _wndproc_cb, 0, 0, None, None, None, None, None, "MesaComputeMinV")
user32.RegisterClassW.argtypes = [ctypes.c_void_p]
user32.RegisterClassW.restype = ctypes.c_ushort
user32.CreateWindowExW.argtypes = [ctypes.c_ulong, ctypes.c_wchar_p,
                                   ctypes.c_wchar_p, ctypes.c_ulong,
                                   ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                   ctypes.c_int, ctypes.c_void_p,
                                   ctypes.c_void_p, ctypes.c_void_p,
                                   ctypes.c_void_p]
user32.CreateWindowExW.restype = ctypes.c_void_p
user32.GetDC.argtypes = [ctypes.c_void_p]
user32.GetDC.restype = ctypes.c_void_p
user32.RegisterClassW(ctypes.byref(wc))
hwnd = user32.CreateWindowExW(0, "MesaComputeMinV", "p", 0, 0, 0, 64, 64,
                              None, None, None, None)
hdc = user32.GetDC(hwnd)


class PFD(ctypes.Structure):
    _fields_ = [("nSize", ctypes.c_ushort), ("nVersion", ctypes.c_ushort),
                ("dwFlags", ctypes.c_ulong), ("iPixelType", ctypes.c_ubyte),
                ("cColorBits", ctypes.c_ubyte), ("cRedBits", ctypes.c_ubyte),
                ("cRedShift", ctypes.c_ubyte), ("cGreenBits", ctypes.c_ubyte),
                ("cGreenShift", ctypes.c_ubyte), ("cBlueBits", ctypes.c_ubyte),
                ("cBlueShift", ctypes.c_ubyte), ("cAlphaBits", ctypes.c_ubyte),
                ("cAlphaShift", ctypes.c_ubyte), ("cAccumBits", ctypes.c_ubyte),
                ("cAccumRedBits", ctypes.c_ubyte),
                ("cAccumGreenBits", ctypes.c_ubyte),
                ("cAccumBlueBits", ctypes.c_ubyte),
                ("cAccumAlphaBits", ctypes.c_ubyte),
                ("cDepthBits", ctypes.c_ubyte),
                ("cStencilBits", ctypes.c_ubyte),
                ("cAuxBuffers", ctypes.c_ubyte), ("iLayerType", ctypes.c_ubyte),
                ("bReserved", ctypes.c_ubyte), ("dwLayerMask", ctypes.c_ulong),
                ("dwVisibleMask", ctypes.c_ulong),
                ("dwDamageMask", ctypes.c_ulong)]


gdi32.ChoosePixelFormat.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
gdi32.ChoosePixelFormat.restype = ctypes.c_int
gdi32.SetPixelFormat.argtypes = [ctypes.c_void_p, ctypes.c_int,
                                 ctypes.c_void_p]
gdi32.SetPixelFormat.restype = ctypes.c_int
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
print("wglCreateContextAttribsARB:", pAttr, flush=True)
FN = ctypes.WINFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
                        ctypes.POINTER(ctypes.c_int))(pAttr)
attribs = (ctypes.c_int * 7)(0x2091, 4, 0x2092, 2, 0x9126, 0x1, 0)
hgl = FN(ctypes.c_void_p(hdc), None, attribs)
print("core 4.2:", hgl, flush=True)
opengl32.wglMakeCurrent(None, None)
opengl32.wglDeleteContext(ctypes.c_void_p(tmp))
if not hgl:
    print("NO_42_CORE_CONTEXT")
    sys.exit(2)
print("make:", opengl32.wglMakeCurrent(ctypes.c_void_p(hdc),
                                       ctypes.c_void_p(hgl)), flush=True)


def proc(name, restype, *argtypes):
    p = opengl32.wglGetProcAddress(name.encode())
    if not p:
        print(f"MISSING {name}", flush=True)
        sys.exit(3)
    fn = ctypes.WINFUNCTYPE(restype, *argtypes)(p)
    fn.argtypes = list(argtypes)
    fn.restype = restype
    return fn


glGetError = proc("glGetError", GLenum)
glGenBuffers = proc("glGenBuffers", None, GLsizei,
                    ctypes.POINTER(GLuint))
glBindBuffer = proc("glBindBuffer", None, GLenum, GLuint)
glBufferData = proc("glBufferData", None, GLenum, GLsizeiptr,
                    ctypes.c_void_p, GLenum)
glBindBufferBase = proc("glBindBufferBase", None, GLenum, GLuint, GLuint)
glGetBufferParameteriv = proc("glGetBufferParameteriv", None, GLenum,
                              GLenum, ctypes.POINTER(GLint))
glCreateShader = proc("glCreateShader", GLuint, GLenum)
glShaderSource = proc("glShaderSource", None, GLuint, GLsizei,
                      ctypes.POINTER(ctypes.c_char_p),
                      ctypes.POINTER(GLint))
glCompileShader = proc("glCompileShader", None, GLuint)
glGetShaderiv = proc("glGetShaderiv", None, GLuint, GLenum,
                     ctypes.POINTER(GLint))
glGetShaderInfoLog = proc("glGetShaderInfoLog", None, GLuint, GLsizei,
                          ctypes.POINTER(GLsizei), ctypes.c_char_p)
glCreateProgram = proc("glCreateProgram", GLuint)
glAttachShader = proc("glAttachShader", None, GLuint, GLuint)
glLinkProgram = proc("glLinkProgram", None, GLuint)
glGetProgramiv = proc("glGetProgramiv", None, GLuint, GLenum,
                      ctypes.POINTER(GLint))
glGetProgramInfoLog = proc("glGetProgramInfoLog", None, GLuint, GLsizei,
                           ctypes.POINTER(GLsizei), ctypes.c_char_p)
glUseProgram = proc("glUseProgram", None, GLuint)
glDispatchCompute = proc("glDispatchCompute", None, GLuint, GLuint, GLuint)
glMemoryBarrier = proc("glMemoryBarrier", None, ctypes.c_uint)
glFlush = proc("glFlush", None)
glFinish = proc("glFinish", None)
glGetBufferSubData = proc("glGetBufferSubData", None, GLenum, GLintptr,
                          GLsizeiptr, ctypes.c_void_p)


def check(step):
    e = glGetError()
    if e != 0:
        errors.append((step, hex(e)))
        print(f"GL_ERROR at {step}: {hex(e)}", flush=True)
    return e


GL_SSBO = 0x90D2
GL_COMPUTE = 0x91B9
GL_STATIC_DRAW = 0x88E4
GL_COMPILE_STATUS = 0x8B81
GL_LINK_STATUS = 0x8B82
GL_INFO_LOG_LENGTH = 0x8B84
GL_BUFFER_SIZE = 0x8764
GL_SHADER_STORAGE_BARRIER = 0x2000

# Three SSBOs, mirroring Blender end_sync (three bindings before dispatch).
bufs = (GLuint * 3)()
glGenBuffers(3, bufs)
check("gen")
print("buffers:", list(bufs), flush=True)
for i in range(3):
    if not bufs[i]:
        print(f"GEN_FAIL slot {i}")
        sys.exit(6)

zero = (ctypes.c_uint * 4)(0, 0, 0, 0)
for i in range(3):
    glBindBuffer(GL_SSBO, bufs[i])
    check(f"bind{i}")
    glBufferData(GL_SSBO, GLsizeiptr(16), ctypes.cast(zero, ctypes.c_void_p),
                 GL_STATIC_DRAW)
    check(f"data{i}")
    size = GLint(0)
    glGetBufferParameteriv(GL_SSBO, GL_BUFFER_SIZE, ctypes.byref(size))
    check(f"querysize{i}")
    print(f"buffer{i} id={bufs[i]} GL_BUFFER_SIZE={size.value}", flush=True)
    if size.value != 16:
        print(f"SIZE_FAIL buffer{i}: got {size.value}, want 16")
        sys.exit(7)
    glBindBufferBase(GL_SSBO, GLuint(i), bufs[i])
    check(f"bindbase{i}")

src = (b"#version 420 core\n"
       b"#extension GL_ARB_compute_shader : require\n"
       b"#extension GL_ARB_shader_storage_buffer_object : require\n"
       b"layout(local_size_x=1) in;\n"
       b"layout(std430, binding=0) buffer Out0 { uint data0[4]; };\n"
       b"layout(std430, binding=1) buffer Out1 { uint data1[4]; };\n"
       b"layout(std430, binding=2) buffer Out2 { uint data2[4]; };\n"
       b"void main(){ uint i = gl_GlobalInvocationID.x;\n"
       b" data0[i] = i*7u+1u; data1[i] = i*3u+2u; data2[i] = i+10u; }\n")
sh = glCreateShader(GL_COMPUTE)
check("createshader")
print("shader:", sh, flush=True)
if not sh:
    print("SHADER_ID_ZERO")
    sys.exit(8)
csrc = ctypes.c_char_p(src)
clen = GLint(len(src))
glShaderSource(sh, 1, ctypes.byref(csrc), ctypes.byref(clen))
check("source")
glCompileShader(sh)
check("compile")
st = GLint(0)
glGetShaderiv(sh, GL_COMPILE_STATUS, ctypes.byref(st))
print("compile status:", st.value, flush=True)
if not st.value:
    ln = GLint(0)
    glGetShaderiv(sh, GL_INFO_LOG_LENGTH, ctypes.byref(ln))
    log = ctypes.create_string_buffer(max(1, ln.value))
    got = GLsizei(0)
    glGetShaderInfoLog(sh, max(1, ln.value), ctypes.byref(got), log)
    print("shader log:", log.value.decode(errors="replace"), flush=True)
    print("COMPILE_FAIL")
    sys.exit(4)
pr = glCreateProgram()
check("createprog")
print("program:", pr, flush=True)
if not pr:
    print("PROGRAM_ID_ZERO")
    sys.exit(8)
glAttachShader(pr, sh)
check("attach")
glLinkProgram(pr)
check("link")
glGetProgramiv(pr, GL_LINK_STATUS, ctypes.byref(st))
print("link status:", st.value, flush=True)
if not st.value:
    ln = GLint(0)
    glGetProgramiv(pr, GL_INFO_LOG_LENGTH, ctypes.byref(ln))
    log = ctypes.create_string_buffer(max(1, ln.value))
    got = GLsizei(0)
    glGetProgramInfoLog(pr, max(1, ln.value), ctypes.byref(got), log)
    print("program log:", log.value.decode(errors="replace"), flush=True)
    print("LINK_FAIL")
    sys.exit(5)
glUseProgram(pr)
check("use")
if os.environ.get("SQ2_TRIANGLE_FIRST"):
    print("triangle-first variant: drawing one triangle...", flush=True)
    glDrawArrays = proc("glDrawArrays", None, GLenum, GLint, GLsizei)
    glCreateShader2 = glCreateShader
    vsrc = (b"#version 420 core\nlayout(location=0) in vec2 p;\n"
            b"void main(){ gl_Position = vec4(p, 0.0, 1.0); }\n")
    fsrc = (b"#version 420 core\nout vec4 c;\n"
            b"void main(){ c = vec4(1.0); }\n")
    GL_VERTEX = 0x8B31
    GL_FRAGMENT = 0x8B30
    GL_ARRAY_BUFFER = 0x8892
    GL_FLOAT = 0x1406
    glGenBuffersNV = proc("glGenBuffers", None, GLsizei,
                           ctypes.POINTER(GLuint))
    vbo = GLuint(0)
    glGenBuffersNV(1, ctypes.byref(vbo))
    check("t-gen")
    glBindBuffer(GL_ARRAY_BUFFER, vbo.value)
    check("t-bind")
    verts = (ctypes.c_float * 6)(-1.0, -1.0, 3.0, -1.0, -1.0, 3.0)
    glBufferData(GL_ARRAY_BUFFER, GLsizeiptr(24),
                 ctypes.cast(verts, ctypes.c_void_p), GL_STATIC_DRAW)
    check("t-data")
    size = GLint(0)
    glGetBufferParameteriv(GL_ARRAY_BUFFER, GL_BUFFER_SIZE,
                            ctypes.byref(size))
    check("t-size")
    print("tri vbo:", vbo.value, "size:", size.value, flush=True)
    vs = glCreateShader2(GL_VERTEX)
    check("t-vs")
    cs = ctypes.c_char_p(vsrc)
    cl = GLint(len(vsrc))
    glShaderSource(vs, 1, ctypes.byref(cs), ctypes.byref(cl))
    check("t-vssrc")
    glCompileShader(vs)
    check("t-vscomp")
    fs = glCreateShader2(GL_FRAGMENT)
    check("t-fs")
    cs = ctypes.c_char_p(fsrc)
    cl = GLint(len(fsrc))
    glShaderSource(fs, 1, ctypes.byref(cs), ctypes.byref(cl))
    check("t-fssrc")
    glCompileShader(fs)
    check("t-fscomp")
    tpr = glCreateProgram()
    check("t-prog")
    glAttachShader(tpr, vs)
    check("t-attvs")
    glAttachShader(tpr, fs)
    check("t-attfs")
    glLinkProgram(tpr)
    check("t-link")
    glGetProgramiv(tpr, GL_LINK_STATUS, ctypes.byref(st))
    print("tri link:", st.value, flush=True)
    print("tri use...", flush=True)
    glUseProgram(tpr)
    check("t-use")
    print("tri used", flush=True)
    glEnableVertexAttribArray = proc("glEnableVertexAttribArray", None,
                                     GLuint)
    glVertexAttribPointer = proc("glVertexAttribPointer", None, GLuint,
                                 GLint, GLenum, ctypes.c_ubyte, GLsizei,
                                 ctypes.c_void_p)
    glGenVertexArrays = proc("glGenVertexArrays", None, GLsizei,
                             ctypes.POINTER(GLuint))
    glBindVertexArray = proc("glBindVertexArray", None, GLuint)
    vao = GLuint(0)
    glGenVertexArrays(1, ctypes.byref(vao))
    check("t-genvao")
    glBindVertexArray(vao.value)
    check("t-bindvao")
    print("tri enable...", flush=True)
    glEnableVertexAttribArray(GLuint(0))
    print("tri enabled", flush=True)
    check("t-enable")
    glVertexAttribPointer(GLuint(0), 2, GL_FLOAT, 0, 0, None)
    check("t-ptr")
    glDrawArrays(0x0004, 0, 3)
    check("t-draw")
    glFinish()
    check("t-finish")
    glUseProgram(pr)
    check("t-reuse")
    print("triangle done", flush=True)
print("dispatching 1x1x1...", flush=True)
glDispatchCompute(GLuint(1), GLuint(1), GLuint(1))
check("dispatch")
glMemoryBarrier(GLuint(GL_SHADER_STORAGE_BARRIER))
check("barrier")
print("glFlush...", flush=True)
glFlush()
check("flush")
print("glFinish...", flush=True)
glFinish()
check("finish")

results = []
for i in range(3):
    glBindBuffer(GL_SSBO, bufs[i])
    check(f"rebind{i}")
    out = (ctypes.c_uint * 4)()
    glGetBufferSubData(GL_SSBO, GLintptr(0), GLsizeiptr(16),
                       ctypes.cast(out, ctypes.c_void_p))
    check(f"readback{i}")
    results.append(list(out))
    print(f"readback{i}:", list(out), flush=True)

want = [[1, 0, 0, 0], [2, 0, 0, 0], [10, 0, 0, 0]]
print("MINIMAL_COMPUTE_PASS" if results == want and not errors
      else "MINIMAL_COMPUTE_FAIL", flush=True)
if errors:
    print("errors seen:", errors, flush=True)
