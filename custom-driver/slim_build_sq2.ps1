# Slim path — build Blender 5.2 Lite ARM64 ON this Surface Pro X (SQ2)
# Target: ~15-20GB total, not 100GB. Workbench-only + EEVEE-SQ2 raster.
# Run in PowerShell as Admin: Set-ExecutionPolicy Bypass -Scope Process; .\slim_build_sq2.ps1
# Time: 4-10 hrs on SQ2 (8 cores, 16GB). Keep plugged in, lid open.

$ErrorActionPreference = "Stop"
$ROOT = "C:\blender-sq2-build"
mkdir $ROOT -Force | Out-Null
cd $ROOT

Write-Host "=== 0. Toolchain check ==="
winget --version
git --version
python --version
# VS Build Tools ARM64 + CMake + Ninja (only what Lite needs)
# If VS already installed, these are no-ops.

Write-Host "=== 1. Install CMake + Ninja (fast) ==="
winget install -e --id Kitware.CMake --silent --accept-package-agreements --accept-source-agreements
winget install -e --id Ninja-build.Ninja --silent --accept-package-agreements --accept-source-agreements

Write-Host "=== 2. Install VS2022 Build Tools ARM64 (slow, ~9GB, keep power on) ==="
# Includes MSVC ARM64 + Windows SDK 20348+ + C++ CMake tools. No full IDE.
winget install -e --id Microsoft.VisualStudio.2022.BuildTools --silent --accept-package-agreements --accept-source-agreements `
  --override "--wait --quiet --add Microsoft.VisualStudio.Workload.VCTools --add Microsoft.VisualStudio.Component.VC.Tools.ARM64 --add Microsoft.VisualStudio.Component.Windows11SDK.22621 --add Microsoft.VisualStudio.Component.VC.CMake.Project --includeRecommended"

Write-Host "=== 3. Shallow clone Blender 5.2.3 (no history) ==="
if (!(Test-Path "$ROOT\blender")) {
  git clone --depth 1 -b v5.2.3 https://projects.blender.org/blender/blender.git blender
}
cd blender

Write-Host "=== 4. Prebuilt ARM64 libs only (no dep rebuild) ==="
# This pulls lib-windows_arm64 matching 5.2 (~8-12GB). Do NOT run make deps.
make update

Write-Host "=== 5. Apply SQ2 patches ==="
# Copy our patches into source (edit locations in comments, line numbers shift):
Copy-Item "$PSScriptRoot\..\frankenbuild\sq2_compat.patch" "$ROOT\blender\sq2_compat.patch" -Force
Copy-Item "$PSScriptRoot\eevee-unclosed\blender_eevee_sq2_fallback.patch" "$ROOT\blender\eevee_sq2.patch" -Force
Write-Host "APPLY BY HAND (search strings, not line numbers):"
Write-Host " - gl_backend.cc: search '30.0.3820' + 'epoxy_gl_version() >= 43' (see sq2_compat.patch)"
Write-Host " - eevee_pipeline.cc: search 'SQ2_EEVEE_RASTER' (see eevee_sq2.patch)"

Write-Host "=== 6. Configure LITE (no Cycles GPU, no USD, no tests) ==="
# Low parallel to survive 16GB: -j4, not -j8. Single config Release only.
make lite BUILD_DIR=build_lite `
  -DCMAKE_BUILD_TYPE=Release `
  -DWITH_CYCLES_DEVICE_CUDA=OFF -DWITH_CYCLES_DEVICE_HIP=OFF -DWITH_CYCLES_DEVICE_ONEAPI=OFF `
  -DWITH_USD=OFF -DWITH_TESTS=OFF -DWITH_DOC_MANPAGE=OFF

Write-Host "=== 7. Build LITE (hours) ==="
cmake --build build_lite --config Release -j 4

Write-Host "=== DONE ==="
Write-Host "Portable folder: $ROOT\blender\build_lite\bin\Release\"
Write-Host "Copy that to C:\blender-sq2\ + drop your shim opengl32.dll + blender.exe.local, launch:"
Write-Host "  blender.exe --factory-startup --gpu-backend OPENGL"
