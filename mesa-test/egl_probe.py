import ctypes, sys, os
egl_path = sys.argv[1]  # full path to Mesa libEGL.dll
gl_path = sys.argv[2]   # full path to Mesa opengl32.dll (desktop GL)
print(f"EGL: {egl_path}\nGL: {gl_path}")
egl = ctypes.WinDLL(egl_path)
gl = ctypes.WinDLL(gl_path)
egl.eglGetDisplay.argtypes=[ctypes.c_void_p]; egl.eglGetDisplay.restype=ctypes.c_void_p
egl.eglInitialize.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_int),ctypes.POINTER(ctypes.c_int)]; egl.eglInitialize.restype=ctypes.c_int
egl.eglBindAPI.argtypes=[ctypes.c_uint]; egl.eglBindAPI.restype=ctypes.c_int
egl.eglChooseConfig.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_int),ctypes.POINTER(ctypes.c_void_p),ctypes.c_int,ctypes.POINTER(ctypes.c_int)]; egl.eglChooseConfig.restype=ctypes.c_int
egl.eglCreatePbufferSurface.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.POINTER(ctypes.c_int)]; egl.eglCreatePbufferSurface.restype=ctypes.c_void_p
egl.eglCreateContext.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.POINTER(ctypes.c_int)]; egl.eglCreateContext.restype=ctypes.c_void_p
egl.eglMakeCurrent.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p]; egl.eglMakeCurrent.restype=ctypes.c_int
egl.eglGetError.argtypes=[]; egl.eglGetError.restype=ctypes.c_int
gl.glGetString.argtypes=[ctypes.c_uint]; gl.glGetString.restype=ctypes.c_char_p
EGL_DEFAULT_DISPLAY=0
EGL_OPENGL_API=0x30A2
EGL_RENDERABLE_TYPE=0x3040; EGL_OPENGL_BIT=0x0008
EGL_SURFACE_TYPE=0x3033; EGL_PBUFFER_BIT=0x0001
EGL_BLUE_SIZE=0x3022; EGL_DEPTH_SIZE=0x3025
EGL_WIDTH=0x3057; EGL_HEIGHT=0x3056
EGL_NONE=0x3038
dpy=egl.eglGetDisplay(ctypes.c_void_p(EGL_DEFAULT_DISPLAY))
print("display:",hex(dpy or 0),"err:",hex(egl.eglGetError()))
maj,minor=ctypes.c_int(),ctypes.c_int()
print("init:",egl.eglInitialize(dpy,ctypes.byref(maj),ctypes.byref(minor)),f"{maj.value}.{minor.value}","err:",hex(egl.eglGetError()))
print("bindAPI:",egl.eglBindAPI(EGL_OPENGL_API),"err:",hex(egl.eglGetError()))
cfg_attribs=(ctypes.c_int*11)(EGL_RENDERABLE_TYPE,EGL_OPENGL_BIT,EGL_SURFACE_TYPE,EGL_PBUFFER_BIT,EGL_BLUE_SIZE,8,EGL_DEPTH_SIZE,24,EGL_NONE)
cfg=(ctypes.c_void_p*1)(); n=ctypes.c_int()
print("choose:",egl.eglChooseConfig(dpy,cfg_attribs,cfg,1,ctypes.byref(n)),"n=",n.value,"err:",hex(egl.eglGetError()))
pb_attribs=(ctypes.c_int*5)(EGL_WIDTH,64,EGL_HEIGHT,64,EGL_NONE)
surf=egl.eglCreatePbufferSurface(dpy,cfg[0],pb_attribs)
print("surf:",hex(surf or 0),"err:",hex(egl.eglGetError()))
ctx=egl.eglCreateContext(dpy,cfg[0],None,None)
print("ctx:",hex(ctx or 0),"err:",hex(egl.eglGetError()))
print("make:",egl.eglMakeCurrent(dpy,surf,surf,ctx),"err:",hex(egl.eglGetError()))
for tag,name in [(0x1F00,"VERSION"),(0x1F01,"RENDERER"),(0x1F02,"VENDOR"),(0x8B8C,"SHADING_LANGUAGE_VERSION")]:
    v=gl.glGetString(tag)
    print(name,"=",v.decode() if v else f"<NULL> err {hex(egl.eglGetError())}")
