import ctypes, sys
egl_path, gles_path = sys.argv[1], sys.argv[2]
egl = ctypes.WinDLL(egl_path)
gles = ctypes.WinDLL(gles_path)
egl.eglGetDisplay.argtypes=[ctypes.c_void_p]; egl.eglGetDisplay.restype=ctypes.c_void_p
egl.eglInitialize.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_int),ctypes.POINTER(ctypes.c_int)]; egl.eglInitialize.restype=ctypes.c_int
egl.eglBindAPI.argtypes=[ctypes.c_uint]; egl.eglBindAPI.restype=ctypes.c_int
egl.eglChooseConfig.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_int),ctypes.POINTER(ctypes.c_void_p),ctypes.c_int,ctypes.POINTER(ctypes.c_int)]; egl.eglChooseConfig.restype=ctypes.c_int
egl.eglCreatePbufferSurface.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.POINTER(ctypes.c_int)]; egl.eglCreatePbufferSurface.restype=ctypes.c_void_p
egl.eglCreateContext.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.POINTER(ctypes.c_int)]; egl.eglCreateContext.restype=ctypes.c_void_p
egl.eglMakeCurrent.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p]; egl.eglMakeCurrent.restype=ctypes.c_int
egl.eglGetError.argtypes=[]; egl.eglGetError.restype=ctypes.c_int
gles.glGetString.argtypes=[ctypes.c_uint]; gles.glGetString.restype=ctypes.c_char_p
EGL_DEFAULT_DISPLAY=0; EGL_OPENGL_ES_API=0x30A0
EGL_RENDERABLE_TYPE=0x3040; EGL_OPENGL_ES3_BIT=0x00000040
EGL_SURFACE_TYPE=0x3033; EGL_PBUFFER_BIT=0x0001
EGL_BLUE_SIZE=0x3022; EGL_NONE=0x3038; EGL_WIDTH=0x3057; EGL_HEIGHT=0x3056
EGL_CONTEXT_MAJOR_VERSION=0x3098; EGL_CONTEXT_MINOR_VERSION=0x30FB
dpy=egl.eglGetDisplay(ctypes.c_void_p(0))
maj,minor=ctypes.c_int(),ctypes.c_int()
egl.eglInitialize(dpy,ctypes.byref(maj),ctypes.byref(minor))
print(f"EGL {maj.value}.{minor.value}")
egl.eglBindAPI(EGL_OPENGL_ES_API)
cfg_attribs=(ctypes.c_int*11)(EGL_RENDERABLE_TYPE,EGL_OPENGL_ES3_BIT,EGL_SURFACE_TYPE,EGL_PBUFFER_BIT,EGL_BLUE_SIZE,8,EGL_NONE)
cfg=(ctypes.c_void_p*1)(); n=ctypes.c_int()
egl.eglChooseConfig(dpy,cfg_attribs,cfg,1,ctypes.byref(n))
print("configs:",n.value)
pb=(ctypes.c_int*5)(EGL_WIDTH,64,EGL_HEIGHT,64,EGL_NONE)
surf=egl.eglCreatePbufferSurface(dpy,cfg[0],pb)
ctx_attribs=(ctypes.c_int*5)(EGL_CONTEXT_MAJOR_VERSION,3,EGL_CONTEXT_MINOR_VERSION,2,EGL_NONE)
ctx=egl.eglCreateContext(dpy,cfg[0],None,ctx_attribs)
print("ctx:",hex(ctx or 0),"err:",hex(egl.eglGetError()))
print("make:",egl.eglMakeCurrent(dpy,surf,surf,ctx))
for tag,name in [(0x1F00,"VERSION"),(0x1F01,"RENDERER"),(0x1F02,"VENDOR"),(0x8B8C,"GLSL")]:
    v=gles.glGetString(tag)
    print(name,"=",(v.decode() if v else "<NULL>"))
