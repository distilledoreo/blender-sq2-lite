function Get-Machine([string]$p) {
  $fs=[IO.File]::OpenRead($p); $br=New-Object IO.BinaryReader($fs)
  $fs.Seek(0x3C,[IO.SeekOrigin]::Begin) | Out-Null; $pe=$br.ReadInt32()
  $fs.Seek($pe,[IO.SeekOrigin]::Begin) | Out-Null; $sig=$br.ReadUInt32(); $m=$br.ReadUInt16()
  $br.Close(); $fs.Close()
  $arch = 'other'; if ($m -eq 0xAA64) { $arch='ARM64' } elseif ($m -eq 0x8664) { $arch='x64' } elseif ($m -eq 0x14C) { $arch='x86' }
  "$p machine=0x$($m.ToString('X4')) $arch"
}
Get-Machine 'C:\Program Files\Adobe\Adobe Photoshop 2026\dxil.dll'
Get-Machine 'C:\Program Files\Adobe\Adobe Photoshop 2027\dxil.dll'
Get-Machine 'C:\Windows\System32\Microsoft-Edge-WebView\dxil.dll'
