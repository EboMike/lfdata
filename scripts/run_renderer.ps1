<#
.SYNOPSIS
    Runs the live_renderer application.

.DESCRIPTION
    Launches the compiled live_renderer executable with optional configuration arguments.
    Automatically ensures the binary is compiled and up to date before launching.
    Passes through any additional command line options (e.g. --lfstats-test-mode) to the binary.

.PARAMETER Config
    Build configuration to run: 'Release' (default) or 'Debug'.

.PARAMETER ConfigFile
    Path to the main YAML configuration file (passed via --config).

.PARAMETER NoBuild
    If specified, skips rebuilding and launches the existing binary immediately.

.PARAMETER ExtraArgs
    Additional command line arguments passed directly down to the live_renderer executable.
#>
[CmdletBinding(PositionalBinding = $false)]
param (
    [string]$Config = 'Release',
    [string]$ConfigFile = '',
    [switch]$NoBuild,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ExtraArgs
)

$ErrorActionPreference = 'Stop'
$repoRoot = (Get-Item $PSScriptRoot).Parent.FullName
Set-Location $repoRoot

$argsList = [System.Collections.Generic.List[string]]::new()
if ($ConfigFile -ne '') {
    $argsList.Add('--config')
    $argsList.Add($ConfigFile)
}

if ($null -ne $ExtraArgs) {
    foreach ($arg in $ExtraArgs) {
        if ($arg -ieq 'debug') {
            $Config = 'Debug'
        } elseif ($arg -ieq 'release') {
            $Config = 'Release'
        } else {
            $argsList.Add($arg)
        }
    }
}

$exePath = "$repoRoot\build\$Config\live_renderer.exe"
if (-not $NoBuild -or -not (Test-Path $exePath)) {
    Write-Host "Ensuring live_renderer ($Config) is up to date..." -ForegroundColor Cyan
    & "$PSScriptRoot\build_renderer.ps1" -Config $Config -Target live_renderer
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to build live_renderer."
        exit 1
    }
}

Write-Host "Starting live_renderer from $exePath..." -ForegroundColor Green
& $exePath @argsList
exit $LASTEXITCODE
