Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
using System.Text;
public class WinC {
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumWindowsProc p, IntPtr l);
  [DllImport("user32.dll")] public static extern bool EnumChildWindows(IntPtr h, EnumWindowsProc p, IntPtr l);
  public delegate bool EnumWindowsProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern IntPtr SendMessage(IntPtr h, uint m, IntPtr w, IntPtr l);
}
'@
$bl = (Get-Process | Where-Object { $_.ProcessName -like 'blender*' }).Id
$cb = {
  param($h, $l)
  $wpid = 0
  [void][WinC]::GetWindowThreadProcessId($h, [ref]$wpid)
  if (($bl -contains $wpid) -and [WinC]::IsWindowVisible($h)) {
    $t = New-Object Text.StringBuilder 256
    [void][WinC]::GetWindowText($h, $t, 256)
    if ($t.ToString() -eq 'Blender') {
      Write-Host "dialog HWND=$h"
      $ccb = {
        param($ch, $cl)
        $ct = New-Object Text.StringBuilder 256
        [void][WinC]::GetWindowText($ch, $ct, 256)
        if ($ct.ToString() -eq 'Continue Anyway') {
          Write-Host 'clicking Continue Anyway'
          [void][WinC]::SendMessage($ch, 0x00F5, [IntPtr]::Zero, [IntPtr]::Zero)
        }
        return $true
      }
      [WinC]::EnumChildWindows($h, $ccb, [IntPtr]::Zero) | Out-Null
    }
  }
  return $true
}
[WinC]::EnumWindows($cb, [IntPtr]::Zero) | Out-Null
