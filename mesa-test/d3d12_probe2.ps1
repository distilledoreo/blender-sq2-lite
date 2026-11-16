Add-Type -TypeDefinition @"
using System; using System.Runtime.InteropServices;
public class DX2 {
  [DllImport("dxgi.dll")] public static extern int CreateDXGIFactory1(ref Guid riid, out IntPtr f);
  [DllImport("d3d12.dll")] public static extern int D3D12CreateDevice(IntPtr adapter, int fl, ref Guid riid, out IntPtr dev);
  [UnmanagedFunctionPointer(CallingConvention.StdCall)] public delegate int EnumA(IntPtr self, UInt32 i, out IntPtr a);
  [UnmanagedFunctionPointer(CallingConvention.StdCall)] public delegate int CheckFS(IntPtr self, int feature, IntPtr data, int size);
}
"@
$IIDF=[Guid]::new("770aae78-f26f-4dba-a829-253c83d1b387")
$fac=[IntPtr]::Zero; $hr=[DX2]::CreateDXGIFactory1([ref]$IIDF,[ref]$fac); "Factory hr=0x$($hr.ToString('X8'))"
$vt=[Runtime.InteropServices.Marshal]::ReadIntPtr($fac)
$fn=[Runtime.InteropServices.Marshal]::ReadIntPtr($vt,7*8)
$enum=[Runtime.InteropServices.Marshal]::GetDelegateForFunctionPointer($fn,[DX2+EnumA])
$ad=[IntPtr]::Zero; $h=$enum.Invoke($fac,[UInt32]0,[ref]$ad); "Adapter0 hr=0x$($h.ToString('X8')) ptr=$ad"
$IID=[Guid]::new("189819f1-1db6-4b80-be9b-80048bfac156")
$dev=[IntPtr]::Zero; $hr2=[DX2]::D3D12CreateDevice($ad,0xb000,[ref]$IID,[ref]$dev); "CreateDevice(11_0,ad0) hr=0x$($hr2.ToString('X8')) dev=$dev"
if ($hr2 -lt 0) { exit 1 }
$vt2=[Runtime.InteropServices.Marshal]::ReadIntPtr($dev)
$fn2=[Runtime.InteropServices.Marshal]::ReadIntPtr($vt2,13*8)
$chk=[Runtime.InteropServices.Marshal]::GetDelegateForFunctionPointer($fn2,[DX2+CheckFS])
$mem=[Runtime.InteropServices.Marshal]::AllocHGlobal(128)
0..31 | ForEach-Object { [Runtime.InteropServices.Marshal]::WriteInt32($mem,$_*4,0) }
$hr3=$chk.Invoke($dev,0,$mem,60); "OPTIONS hr=0x$($hr3.ToString('X8'))"
if ($hr3 -ge 0) {
  $v=New-Object int[] 16; [Runtime.InteropServices.Marshal]::Copy($mem,$v,0,16)
  "ResourceBindingTier(4)=$($v[4]) TypedUAVLoadAdditionalFormats(6)=$($v[6]) ROVs(7)=$($v[7]) ConservRast(8)=$($v[8])"
}
[Runtime.InteropServices.Marshal]::WriteInt32($mem,0,0x60)
$hr4=$chk.Invoke($dev,12,$mem,4)
$sm=[Runtime.InteropServices.Marshal]::ReadInt32($mem,0)
"SHADER_MODEL hr=0x$($hr4.ToString('X8')) highest=0x$($sm.ToString('X8'))"
