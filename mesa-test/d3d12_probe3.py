import ctypes
class GUID(ctypes.Structure):
    _fields_=[("D1",ctypes.c_ulong),("D2",ctypes.c_ushort),("D3",ctypes.c_ushort),("D4",ctypes.c_ubyte*8)]
def G(s):
    a,b,c,d,e=s.split("-")
    return GUID(int(a,16),int(b,16),int(c,16),(ctypes.c_ubyte*8)(int(d[:2],16),int(d[2:],16),*[int(e[i:i+2],16) for i in range(0,12,2)]))
dxgi=ctypes.WinDLL("dxgi.dll"); d3d12=ctypes.WinDLL("d3d12.dll")
dxgi.CreateDXGIFactory1.argtypes=[ctypes.POINTER(GUID),ctypes.POINTER(ctypes.c_void_p)]; dxgi.CreateDXGIFactory1.restype=ctypes.c_long
fac=ctypes.c_void_p()
print("factory hr=0x%08X"%(dxgi.CreateDXGIFactory1(ctypes.byref(G("770aae78-f26f-4dba-a829-253c83d1b387")),ctypes.byref(fac))&0xFFFFFFFF))
vtab=(ctypes.c_void_p*1).from_address(fac.value)[0]
fns=(ctypes.c_void_p*20).from_address(vtab)
FN=ctypes.WINFUNCTYPE(ctypes.c_long,ctypes.c_void_p,ctypes.c_uint,ctypes.POINTER(ctypes.c_void_p))
enum=FN(fns[7])
ad=ctypes.c_void_p(); print("enum hr=0x%08X"%(enum(fac.value,0,ctypes.byref(ad))&0xFFFFFFFF),"adapter=",hex(ad.value or 0))
d3d12.D3D12CreateDevice.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.POINTER(GUID),ctypes.POINTER(ctypes.c_void_p)]; d3d12.D3D12CreateDevice.restype=ctypes.c_long
IID=G("189819f1-1db6-4b80-be9b-80048bfac156")
for fl,name in [(0xb000,"11_0"),(0xc100,"12_1")]:
    dev=ctypes.c_void_p()
    print(f"CreateDevice({name}) hr=0x{d3d12.D3D12CreateDevice(ad.value,fl,ctypes.byref(IID),ctypes.byref(dev))&0xFFFFFFFF:08X} dev={hex(dev.value or 0)}")
    if dev.value:
        # CheckFeatureSupport = vtable[13]: int(self, feature, data, size)
        vt2=(ctypes.c_void_p*20).from_address((ctypes.c_void_p*1).from_address(dev.value)[0])
        CF=ctypes.WINFUNCTYPE(ctypes.c_long,ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p,ctypes.c_int)
        chk=CF(vt2[13])
        mem=(ctypes.c_int*32)()
        print(" OPTIONS hr=0x%08X"%(chk(dev.value,0,mem,60)&0xFFFFFFFF))
        print(" TypedUAV(6)=%d ROVs(7)=%d BindTier(4)=%d"%(mem[6],mem[7],mem[4]))
        sm=(ctypes.c_int*1)(0x60)
        print(" SHADER_MODEL hr=0x%08X highest=0x%08X"%(chk(dev.value,12,sm,4)&0xFFFFFFFF,sm[0]&0xFFFFFFFF))
        break
