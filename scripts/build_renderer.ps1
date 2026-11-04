<#
.SYNOPSIS
    Builds the live_renderer C++ binary and test suite.

.DESCRIPTION
    Configures and builds live_renderer using CMake and MSVC.

.PARAMETER Config
    Build configuration: 'Release' (default) or 'Debug'.

.PARAMETER Target
    CMake target to build: 'all' (default), 'live_renderer', or 'live_renderer_tests'.

.PARAMETER Clean
    If specified, removes existing build directory before building.
#>
param (
    [string]$Config = 'Release',
    [string]$Target = 'all',
    [switch]$Clean
)

$ErrorActionPreference = 'Stop'
$repoRoot = (Get-Item $PSScriptRoot).Parent.FullName
Set-Location $repoRoot

if ($Clean -and (Test-Path "$repoRoot\build")) {
    Write-Host "Cleaning build directory..." -ForegroundColor Cyan
    Remove-Item -Recurse -Force "$repoRoot\build"
}

# Find Visual Studio Developer Environment
$vcvarsPaths = @(
    "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat",
    "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat",
    "C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\VC\Auxiliary\Build\vcvars64.bat"
)

$vcvars = $null
foreach ($path in $vcvarsPaths) {
    if (Test-Path $path) {
        $vcvars = $path
        break
    }
}

if (-not $vcvars) {
    Write-Error "Could not find Visual Studio vcvars64.bat. Please ensure MSVC is installed."
    exit 1
}

# Backup previous version to last_known_good if executable exists in target dir
$targetDir = "$repoRoot\build\$Config"
$lastKnownGoodDir = "$targetDir\last_known_good"
if (Test-Path $targetDir) {
    $existingExes = Get-ChildItem -Path $targetDir -Filter *.exe -File
    if ($existingExes.Count -gt 0) {
        Write-Host "Backing up previous version to last_known_good..." `
            -ForegroundColor Cyan
        if (-not (Test-Path $lastKnownGoodDir)) {
            New-Item -ItemType Directory -Path $lastKnownGoodDir -Force |
                Out-Null
        }
        foreach ($exe in $existingExes) {
            Copy-Item -Path $exe.FullName -Destination $lastKnownGoodDir -Force
            $pdb = [System.IO.Path]::ChangeExtension($exe.FullName, ".pdb")
            if (Test-Path $pdb) {
                Copy-Item -Path $pdb -Destination $lastKnownGoodDir -Force
            }
        }
    }
}

Write-Host "Configuring and building live_renderer ($Config)..." -ForegroundColor Green

$cmd = "`"$vcvars`" && cmake -B build -S src/live_renderer -DYAML_MSVC_SHARED_RT=ON"
if ($Target -eq 'all') {
    $cmd += " && cmake --build build --config $Config"
} else {
    $cmd += " && cmake --build build --config $Config --target $Target"
}

cmd.exe /c $cmd

if ($LASTEXITCODE -eq 0) {
    Write-Host "Build completed successfully!" -ForegroundColor Green
} else {
    Write-Error "Build failed with exit code $LASTEXITCODE."
}

