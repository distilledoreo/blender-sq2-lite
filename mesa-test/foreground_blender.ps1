Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
using System.Text;
public class Win {
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumWindowsProc p, IntPtr l);
  public delegate bool EnumWindowsProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
}
'@
$bl = (Get-Process | Where-Object { $_.ProcessName -like 'blender*' }).Id
Write-Host "blender pids: $bl"
$cb = {
  param($h, $l)
  $wpid = 0
  [void][Win]::GetWindowThreadProcessId($h, [ref]$wpid)
  if ($bl -contains $wpid -and [Win]::IsWindowVisible($h)) {
    $t = New-Object Text.StringBuilder 256
    [void][Win]::GetWindowText($h, $t, 256)
    Write-Host "HWND=$h TITLE='$($t.ToString())'"
    [void][Win]::ShowWindow($h, 9)
    [void][Win]::SetForegroundWindow($h)
  }
  return $true
}
[Win]::EnumWindows($cb, [IntPtr]::Zero) | Out-Null
