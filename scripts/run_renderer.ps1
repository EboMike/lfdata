<#
.SYNOPSIS
    Runs the live_renderer application.

.DESCRIPTION
    Launches the compiled live_renderer executable with optional configuration arguments.
    Automatically ensures the binary is compiled and up to date before launching.

.PARAMETER Config
    Build configuration to run: 'Release' (default) or 'Debug'.

.PARAMETER ConfigFile
    Path to the main YAML configuration file (passed via --config).

.PARAMETER NoBuild
    If specified, skips rebuilding and launches the existing binary immediately.
#>
param (
    [string]$Config = 'Release',
    [string]$ConfigFile = '',
    [switch]$NoBuild
)

$ErrorActionPreference = 'Stop'
$repoRoot = (Get-Item $PSScriptRoot).Parent.FullName
Set-Location $repoRoot

$exePath = "$repoRoot\build\$Config\live_renderer.exe"
if (-not $NoBuild -or -not (Test-Path $exePath)) {
    Write-Host "Ensuring live_renderer ($Config) is up to date..." -ForegroundColor Cyan
    & "$PSScriptRoot\build_renderer.ps1" -Config $Config -Target live_renderer
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to build live_renderer."
        exit 1
    }
}

$argsList = @()
if ($ConfigFile -ne '') {
    $argsList += "--config"
    $argsList += $ConfigFile
}

Write-Host "Starting live_renderer from $exePath..." -ForegroundColor Green
& $exePath @argsList
