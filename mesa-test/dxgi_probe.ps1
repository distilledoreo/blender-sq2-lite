Add-Type -TypeDefinition @"
using System; using System.Runtime.InteropServices;
public class DXGI {
  [DllImport("dxgi.dll")] public static extern int CreateDXGIFactory1(ref Guid riid, out IntPtr factory);
  [UnmanagedFunctionPointer(CallingConvention.StdCall)] public delegate int EnumAdapters1(IntPtr self, uint i, out IntPtr adapter);
  [UnmanagedFunctionPointer(CallingConvention.StdCall)] public delegate int GetDesc(IntPtr self, IntPtr descPtr);
}
"@
$IIDF = [Guid]::new("770aae78-f26f-4dba-a829-253c83d1b387")
$fac=[IntPtr]::Zero
$hr=[DXGI]::CreateDXGIFactory1([ref]$IIDF,[ref]$fac)
"Factory hr=0x$($hr.ToString('X8')) fac=$fac"
if($hr -lt 0){exit 1}
$vt=[Runtime.InteropServices.Marshal]::ReadIntPtr($fac)
# IDXGIFactory1 vtable: IUnknown(3)+Factory(4: EnumAdapters,MakeWindowAssociation,GetWindowAssociation,CreateSwapChain)+Factory1(2: EnumAdapters1,IsCurrent) -> EnumAdapters1 index = 3+4+0? Actually Factory has 4 methods after IUnknown? EnumAdapters(3),MakeWindowAssoc(4),GetWindowAssoc(5),CreateSwapChain(6), then Factory1 EnumAdapters1(7),IsCurrent(8). So index 7.
$fn=[Runtime.InteropServices.Marshal]::ReadIntPtr($vt,7*8)
$enum=[Runtime.InteropServices.Marshal]::GetDelegateForFunctionPointer($fn,[DXGI+EnumAdapters1])
for($i=0;$i -lt 4;$i++){
  $ad=[IntPtr]::Zero; $h=$enum.Invoke($fac,[uint]$i,[ref]$ad)
  "Adapter ${i}: hr=0x$($h.ToString('X8')) ptr=$ad"
}
