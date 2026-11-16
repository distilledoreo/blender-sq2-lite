"""Minimal compute test (no Blender): 4.2 core ctx, one SSBO, one compute
shader writing via gl_GlobalInvocationID, 1x1x1 dispatch, glFinish,
readback + compare. Prints PASS/FAIL and every GL error seen."""
import ctypes, sys

mesa_gl = sys.argv[1]
opengl32 = ctypes.WinDLL(mesa_gl)
user32 = ctypes.WinDLL("user32.dll"); gdi32 = ctypes.WinDLL("gdi32.dll")
opengl32.wglGetProcAddress.argtypes = [ctypes.c_char_p]
opengl32.wglGetProcAddress.restype = ctypes.c_void_p
opengl32.wglCreateContext.argtypes = [ctypes.c_void_p]
opengl32.wglCreateContext.restype = ctypes.c_void_p
opengl32.wglMakeCurrent.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
opengl32.wglMakeCurrent.restype = ctypes.c_int

errors = []
def check(step):
    e = glGetError()
    if e != 0:
        errors.append((step, hex(e)))
        print(f"GL_ERROR at {step}: {hex(e)}", flush=True)

WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_int64, ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint64, ctypes.c_int64)
def wndproc(h, m, w, l):
    return user32.DefWindowProcW(ctypes.c_void_p(h or 0), m, ctypes.c_void_p(w or 0), ctypes.c_void_p(l or 0))
class WC(ctypes.Structure):
    _fields_ = [("s", ctypes.c_uint), ("p", WNDPROC), ("a", ctypes.c_int), ("b", ctypes.c_int),
                ("c", ctypes.c_void_p), ("d", ctypes.c_void_p), ("e", ctypes.c_void_p),
                ("f", ctypes.c_void_p), ("g", ctypes.c_wchar_p), ("h", ctypes.c_wchar_p)]
wc = WC(0, WNDPROC(wndproc), 0, 0, None, None, None, None, None, "MesaComputeMin")
user32.RegisterClassW(ctypes.byref(wc))
hwnd = user32.CreateWindowExW(0, "MesaComputeMin", "p", 0, 0, 0, 64, 64, None, None, None, None)
hdc = user32.GetDC(hwnd)
class PFD(ctypes.Structure):
    _fields_ = [("nSize", ctypes.c_ushort), ("nVersion", ctypes.c_ushort), ("dwFlags", ctypes.c_ulong),
                ("iPixelType", ctypes.c_ubyte), ("cColorBits", ctypes.c_ubyte), ("cRedBits", ctypes.c_ubyte),
                ("cRedShift", ctypes.c_ubyte), ("cGreenBits", ctypes.c_ubyte), ("cGreenShift", ctypes.c_ubyte),
                ("cBlueBits", ctypes.c_ubyte), ("cBlueShift", ctypes.c_ubyte), ("cAlphaBits", ctypes.c_ubyte),
                ("cAlphaShift", ctypes.c_ubyte), ("cAccumBits", ctypes.c_ubyte), ("cAccumRedBits", ctypes.c_ubyte),
                ("cAccumGreenBits", ctypes.c_ubyte), ("cAccumBlueBits", ctypes.c_ubyte), ("cAccumAlphaBits", ctypes.c_ubyte),
                ("cDepthBits", ctypes.c_ubyte), ("cStencilBits", ctypes.c_ubyte), ("cAuxBuffers", ctypes.c_ubyte),
                ("iLayerType", ctypes.c_ubyte), ("bReserved", ctypes.c_ubyte), ("dwLayerMask", ctypes.c_ulong),
                ("dwVisibleMask", ctypes.c_ulong), ("dwDamageMask", ctypes.c_ulong)]
pfd = PFD(); pfd.nSize = ctypes.sizeof(PFD); pfd.nVersion = 1
pfd.dwFlags = 0x25; pfd.cColorBits = 24; pfd.cDepthBits = 24; pfd.cStencilBits = 8
fmt = gdi32.ChoosePixelFormat(hdc, ctypes.byref(pfd)); gdi32.SetPixelFormat(hdc, fmt, ctypes.byref(pfd))
tmp = opengl32.wglCreateContext(ctypes.c_void_p(hdc))
opengl32.wglMakeCurrent(ctypes.c_void_p(hdc), ctypes.c_void_p(tmp))
pAttr = opengl32.wglGetProcAddress(b"wglCreateContextAttribsARB")
print("wglCreateContextAttribsARB:", pAttr, flush=True)
FN = ctypes.WINFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_int))(pAttr)
attribs = (ctypes.c_int * 7)(0x2091, 4, 0x2092, 2, 0x9126, 0x1, 0)
hgl = FN(ctypes.c_void_p(hdc), None, attribs)
print("core 4.2:", hgl, flush=True)
opengl32.wglMakeCurrent(None, None); opengl32.wglDeleteContext(ctypes.c_void_p(tmp))
if not hgl:
    print("NO_42_CORE_CONTEXT"); sys.exit(2)
print("make:", opengl32.wglMakeCurrent(ctypes.c_void_p(hdc), ctypes.c_void_p(hgl)), flush=True)

def proc(name, restype, *argtypes):
    p = opengl32.wglGetProcAddress(name.encode())
    if not p:
        print(f"MISSING {name}", flush=True); sys.exit(3)
    return ctypes.WINFUNCTYPE(restype, *argtypes)(p)

glGetError = proc("glGetError", ctypes.c_uint)
glGenBuffers = proc("glGenBuffers", None, ctypes.c_int, ctypes.POINTER(ctypes.c_uint))
glBindBuffer = proc("glBindBuffer", None, ctypes.c_uint, ctypes.c_uint)
glBufferData = proc("glBufferData", None, ctypes.c_uint, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_uint)
glBindBufferBase = proc("glBindBufferBase", None, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint)
glCreateShader = proc("glCreateShader", ctypes.c_uint, ctypes.c_uint)
glShaderSource = proc("glShaderSource", None, ctypes.c_uint, ctypes.c_int, ctypes.POINTER(ctypes.c_char_p), ctypes.POINTER(ctypes.c_int))
glCompileShader = proc("glCompileShader", None, ctypes.c_uint)
glGetShaderiv = proc("glGetShaderiv", None, ctypes.c_uint, ctypes.c_uint, ctypes.POINTER(ctypes.c_int))
glGetShaderInfoLog = proc("glGetShaderInfoLog", None, ctypes.c_uint, ctypes.c_int, ctypes.POINTER(ctypes.c_int), ctypes.c_char_p)
glCreateProgram = proc("glCreateProgram", ctypes.c_uint)
glAttachShader = proc("glAttachShader", None, ctypes.c_uint, ctypes.c_uint)
glLinkProgram = proc("glLinkProgram", None, ctypes.c_uint)
glGetProgramiv = proc("glGetProgramiv", None, ctypes.c_uint, ctypes.c_uint, ctypes.POINTER(ctypes.c_int))
glGetProgramInfoLog = proc("glGetProgramInfoLog", None, ctypes.c_uint, ctypes.c_int, ctypes.POINTER(ctypes.c_int), ctypes.c_char_p)
glUseProgram = proc("glUseProgram", None, ctypes.c_uint)
glDispatchCompute = proc("glDispatchCompute", None, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint)
glMemoryBarrier = proc("glMemoryBarrier", None, ctypes.c_uint)
glFlush = proc("glFlush", None)
glFinish = proc("glFinish", None)
glGetBufferSubData = proc("glGetBufferSubData", None, ctypes.c_uint, ctypes.c_int64, ctypes.c_size_t, ctypes.c_void_p)

GL_SSBO = 0x90D2; GL_COMPUTE = 0x91B9; GL_STATIC_DRAW = 0x88E4
GL_COMPILE_STATUS = 0x8B81; GL_LINK_STATUS = 0x8B82; GL_INFO_LOG_LENGTH = 0x8B84
GL_SHADER_STORAGE_BARRIER = 0x2000

buf = ctypes.c_uint(0)
glGenBuffers(1, ctypes.byref(buf)); check("gen")
print("buffer:", buf.value, flush=True)
glBindBuffer(GL_SSBO, buf.value); check("bind")
zero = (ctypes.c_uint * 4)(0, 0, 0, 0)
glBufferData(GL_SSBO, 16, zero, GL_STATIC_DRAW); check("data")
glBindBufferBase(GL_SSBO, 0, buf.value); check("bindbase")

src = b"#version 420 core\n#extension GL_ARB_compute_shader : require\n#extension GL_ARB_shader_storage_buffer_object : require\nlayout(local_size_x=1) in;\nlayout(std430, binding=0) buffer Out { uint data[4]; };\nvoid main(){ uint i = gl_GlobalInvocationID.x; data[i] = i*7u+1u; }\n"
sh = glCreateShader(GL_COMPUTE); check("createshader")
csrc = ctypes.c_char_p(src); clen = ctypes.c_int(len(src))
glShaderSource(sh, 1, ctypes.byref(csrc), ctypes.byref(clen)); check("source")
glCompileShader(sh); check("compile")
st = ctypes.c_int(0); glGetShaderiv(sh, GL_COMPILE_STATUS, ctypes.byref(st))
print("compile status:", st.value, flush=True)
if not st.value:
    ln = ctypes.c_int(0); glGetShaderiv(sh, GL_INFO_LOG_LENGTH, ctypes.byref(ln))
    log = ctypes.create_string_buffer(max(1, ln.value)); glGetShaderInfoLog(sh, ln.value, None, log)
    print("shader log:", log.value.decode(errors="replace"), flush=True)
    print("COMPILE_FAIL"); sys.exit(4)
pr = glCreateProgram(); check("createprog")
glAttachShader(pr, sh); check("attach")
glLinkProgram(pr); check("link")
glGetProgramiv(pr, GL_LINK_STATUS, ctypes.byref(st))
print("link status:", st.value, flush=True)
if not st.value:
    ln = ctypes.c_int(0); glGetProgramiv(pr, GL_INFO_LOG_LENGTH, ctypes.byref(ln))
    log = ctypes.create_string_buffer(max(1, ln.value)); glGetProgramInfoLog(pr, ln.value, None, log)
    print("program log:", log.value.decode(errors="replace"), flush=True)
    print("LINK_FAIL"); sys.exit(5)
glUseProgram(pr); check("use")
print("dispatching 1x1x1...", flush=True)
glDispatchCompute(1, 1, 1); check("dispatch")
glMemoryBarrier(GL_SHADER_STORAGE_BARRIER); check("barrier")
print("glFlush...", flush=True)
glFlush(); check("flush")
print("glFinish...", flush=True)
glFinish(); check("finish")
out = (ctypes.c_uint * 4)()
glGetBufferSubData(GL_SSBO, 0, 16, out); check("readback")
vals = list(out)
print("readback:", vals, flush=True)
print("MINIMAL_COMPUTE_PASS" if vals == [1, 0, 0, 0] and not errors else "MINIMAL_COMPUTE_FAIL", flush=True)
if errors:
    print("errors seen:", errors, flush=True)
