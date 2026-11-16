Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
using System.Text;
public class Win2 {
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumWindowsProc p, IntPtr l);
  public delegate bool EnumWindowsProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
  [DllImport("user32.dll")] public static extern bool BringWindowToTop(IntPtr h);
}
'@
$bl = (Get-Process | Where-Object { $_.ProcessName -like 'blender*' }).Id
$cb = {
  param($h, $l)
  $wpid = 0
  [void][Win2]::GetWindowThreadProcessId($h, [ref]$wpid)
  if ([Win2]::IsWindowVisible($h)) {
    $t = New-Object Text.StringBuilder 256
    [void][Win2]::GetWindowText($h, $t, 256)
    $title = $t.ToString()
    if ($title.Length -gt 0 -and !($bl -contains $wpid)) {
      [void][Win2]::ShowWindow($h, 6)
    }
  }
  return $true
}
[Win2]::EnumWindows($cb, [IntPtr]::Zero) | Out-Null
Start-Sleep -Milliseconds 500
$cb2 = {
  param($h, $l)
  $wpid = 0
  [void][Win2]::GetWindowThreadProcessId($h, [ref]$wpid)
  if (($bl -contains $wpid) -and [Win2]::IsWindowVisible($h)) {
    $t = New-Object Text.StringBuilder 256
    [void][Win2]::GetWindowText($h, $t, 256)
    $title = $t.ToString()
    if ($title -like '*Blender 5.2.3*') {
      Write-Host "raising main: $title"
      [void][Win2]::ShowWindow($h, 3)
      [void][Win2]::BringWindowToTop($h)
      [void][Win2]::SetForegroundWindow($h)
    }
  }
  return $true
}
[Win2]::EnumWindows($cb2, [IntPtr]::Zero) | Out-Null
