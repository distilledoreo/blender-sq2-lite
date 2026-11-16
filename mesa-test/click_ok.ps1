Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
using System.Text;
public class Win3 {
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumWindowsProc p, IntPtr l);
  [DllImport("user32.dll")] public static extern bool EnumChildWindows(IntPtr h, EnumWindowsProc p, IntPtr l);
  public delegate bool EnumWindowsProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern IntPtr SendMessage(IntPtr h, uint m, IntPtr w, IntPtr l);
}
'@
$bl = (Get-Process | Where-Object { $_.ProcessName -like 'blender*' }).Id
$cb = {
  param($h, $l)
  $wpid = 0
  [void][Win3]::GetWindowThreadProcessId($h, [ref]$wpid)
  if (($bl -contains $wpid) -and [Win3]::IsWindowVisible($h)) {
    $t = New-Object Text.StringBuilder 256
    [void][Win3]::GetWindowText($h, $t, 256)
    if ($t.ToString() -eq 'Blender') {
      Write-Host "dialog HWND=$h"
      [void][Win3]::SetForegroundWindow($h)
      $ccb = {
        param($ch, $cl)
        $ct = New-Object Text.StringBuilder 256
        [void][Win3]::GetWindowText($ch, $ct, 256)
        $label = $ct.ToString()
        if ($label.Length -gt 0) { Write-Host "  child HWND=$ch LABEL='$label'" }
        if ($label -eq 'OK') {
          Write-Host "  clicking OK"
          [void][Win3]::SendMessage($ch, 0x00F5, [IntPtr]::Zero, [IntPtr]::Zero)
        }
        return $true
      }
      [Win3]::EnumChildWindows($h, $ccb, [IntPtr]::Zero) | Out-Null
    }
  }
  return $true
}
[Win3]::EnumWindows($cb, [IntPtr]::Zero) | Out-Null
