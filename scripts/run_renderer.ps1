<#
.SYNOPSIS
    Runs the live_renderer application.

.DESCRIPTION
    Launches the compiled live_renderer executable with optional configuration arguments.

.PARAMETER Config
    Build configuration to run: 'Release' (default) or 'Debug'.

.PARAMETER ConfigFile
    Path to the main YAML configuration file (passed via --config).
#>
param (
    [string]$Config = 'Release',
    [string]$ConfigFile = ''
)

$ErrorActionPreference = 'Stop'
$repoRoot = (Get-Item $PSScriptRoot).Parent.FullName
Set-Location $repoRoot

$exePath = "$repoRoot\build\$Config\live_renderer.exe"
if (-not (Test-Path $exePath)) {
    Write-Host "Executable not found at $exePath. Building first..." -ForegroundColor Yellow
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

