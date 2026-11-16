Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public class D3D12Native {
  [DllImport("d3d12.dll")] public static extern int D3D12CreateDevice(IntPtr adapter, int fl, ref Guid riid, out IntPtr dev);
  [UnmanagedFunctionPointer(CallingConvention.StdCall)] public delegate int CheckFS(IntPtr self, int feature, IntPtr data, int size);
}
"@
$IID = [Guid]::new("189819f1-1db6-4b80-be9b-80048bfac156")
# FL enum values: 11_0=0xb000 etc; use 11_0 to maximize success (dxdiag max is 12_1)
$dev = [IntPtr]::Zero
$hr = [D3D12Native]::D3D12CreateDevice([IntPtr]::Zero, 0xb000, [ref]$IID, [ref]$dev)
"CreateDevice(11_0): hr=0x$($hr.ToString('X8')) dev=$dev"
if ($hr -lt 0 -or $dev -eq 0) { exit 1 }
$vt = [Runtime.InteropServices.Marshal]::ReadIntPtr($dev)
$fn = [Runtime.InteropServices.Marshal]::ReadIntPtr($vt, 13*8)
$chk = [Runtime.InteropServices.Marshal]::GetDelegateForFunctionPointer($fn, [D3D12Native+CheckFS])
# OPTIONS (feature 0), size = 15 ints = 60 bytes (older layout); use 60 then try larger
$buf = New-Object byte[] 128
$h = [Runtime.InteropServices.Marshal]::AllocHGlobal(128)
[Runtime.InteropServices.Marshal]::Copy($buf,0,$h,128)
$hr2 = $chk.Invoke($dev, 0, $h, 60)
"OPTIONS hr=0x$($hr2.ToString('X8'))"
$vals = New-Object int[] 32
[Runtime.InteropServices.Marshal]::Copy($h,$vals,0,32)
"TypedUAVLoadAdditionalFormats (idx6) = $($vals[6])"
"ROVsSupported(idx7) = $($vals[7])"
"ResourceBindingTier(idx4) = $($vals[4])"
"ConservativeRasterizationTier(idx8) = $($vals[8])"
# SHADER_MODEL (feature 12), struct = 1 int in, returns highest
[Runtime.InteropServices.Marshal]::WriteInt32($h, 0x60)  # ask for SM 6.0 (0x60)? actually input ignored, output highest
$hr3 = $chk.Invoke($dev, 12, $h, 4)
$sm = [Runtime.InteropServices.Marshal]::ReadInt32($h)
"SHADER_MODEL hr=0x$($hr3.ToString('X8')) highest=0x$($sm.ToString('X')) ($sm)"
# FEATURE_LEVELS (feature 1): struct {NumLevels, pLevels, MaxSupported}
"done"
