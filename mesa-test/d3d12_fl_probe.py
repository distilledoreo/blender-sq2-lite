import ctypes
d3d12 = ctypes.WinDLL("d3d12.dll")
# HRESULT D3D12CreateDevice(IUnknown*, D3D_FEATURE_LEVEL, REFIID, void**)
# Try max feature level by attempting device creation at each level
import uuid
# IID_ID3D12Device = {189819f1-1db6-4b80-be9b-80048bfac156}
class GUID(ctypes.Structure):
    _fields_=[("Data1",ctypes.c_ulong),("Data2",ctypes.c_ushort),("Data3",ctypes.c_ushort),("Data4",ctypes.c_ubyte*8)]
def guid(s):
    import re
    a,b,c,d,e = re.split(r'[-]',s)
    d0=int(d[:2],16); d1=int(d[2:],16)
    em=[int(e[i:i+2],16) for i in range(0,12,2)]
    return GUID(int(a,16),int(b,16),int(c,16),(ctypes.c_ubyte*8)(d0,d1,*em))
IID = guid("189819f1-1db6-4b80-be9b-80048bfac156")
FL = {0xb000:"11_0",0xb100:"11_1",0xc000:"12_0",0xc100:"12_1",0xc200:"12_2"}
d3d12.D3D12CreateDevice.argtypes=[ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p)]
d3d12.D3D12CreateDevice.restype=ctypes.c_long  # HRESULT
for fl in [0xc200,0xc100,0xc000,0xb100,0xb000]:
    pp=ctypes.c_void_p()
    hr = d3d12.D3D12CreateDevice(None, fl, ctypes.byref(IID), ctypes.byref(pp))
    print(f"FL {FL[fl]} (0x{fl:x}): hr=0x{hr&0xFFFFFFFF:08x} {'OK' if hr>=0 else 'fail'} dev={hex(pp.value or 0)}")
    if pp.value:
        # release
        ctypes.cast(pp.value, ctypes.POINTER(ctypes.c_void_p))
