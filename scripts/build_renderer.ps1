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

function Find-VcVars64 {
    $vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
    if (Test-Path $vswhere) {
        $installPath = & $vswhere -latest -products * `
            -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 `
            -property installationPath 2>$null
        if ($installPath) {
            $candidate = Join-Path $installPath "VC\Auxiliary\Build\vcvars64.bat"
            if (Test-Path $candidate) {
                return $candidate
            }
        }
    }

    $vcvarsPaths = @(
        "${env:ProgramFiles}\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat",
        "${env:ProgramFiles}\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat",
        "${env:ProgramFiles}\Microsoft Visual Studio\2022\Professional\VC\Auxiliary\Build\vcvars64.bat",
        "${env:ProgramFiles}\Microsoft Visual Studio\2022\Enterprise\VC\Auxiliary\Build\vcvars64.bat",
        "${env:ProgramFiles(x86)}\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat",
        "${env:ProgramFiles}\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat",
        "${env:ProgramFiles(x86)}\Microsoft Visual Studio\2019\Community\VC\Auxiliary\Build\vcvars64.bat",
        "${env:ProgramFiles(x86)}\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
    )

    foreach ($path in $vcvarsPaths) {
        if (Test-Path $path) {
            return $path
        }
    }

    return $null
}

function Get-ExistingVsInstall {
    $vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
    if (-not (Test-Path $vswhere)) {
        return $null
    }

    $json = & $vswhere -latest -products * -format json 2>$null | Out-String
    if (-not $json) {
        return $null
    }

    $parsed = $json | ConvertFrom-Json
    if ($parsed -and $parsed.Count -gt 0) {
        return $parsed[0]
    }
    return $null
}

function Install-Msvc {
    $setupExe = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\setup.exe"
    $vsInstall = Get-ExistingVsInstall

    if ($vsInstall -and (Test-Path $setupExe)) {
        $installPath = $vsInstall.installationPath
        $workload = if ($vsInstall.productId -eq "Microsoft.VisualStudio.Product.BuildTools") {
            "Microsoft.VisualStudio.Workload.VCTools"
        } else {
            "Microsoft.VisualStudio.Workload.NativeDesktop"
        }

        Write-Host "MSVC is missing. Attempting to install $workload into '$installPath'..." -ForegroundColor Yellow
        $installerArgs = @(
            "modify",
            "--installPath", "`"$installPath`"",
            "--add", $workload,
            "--includeRecommended",
            "--passive",
            "--norestart"
        )
        try {
            $proc = Start-Process -FilePath $setupExe `
                -ArgumentList $installerArgs -Verb RunAs -Wait -PassThru
            return ($proc.ExitCode -eq 0)
        } catch {
            Write-Warning "Failed to launch Visual Studio Installer: $($_.Exception.Message)"
            return $false
        }
    }

    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if ($winget) {
        Write-Host "MSVC is missing. Attempting to install Visual Studio 2022 Build Tools via winget..." -ForegroundColor Yellow
        try {
            & $winget.Source install --id Microsoft.VisualStudio.2022.BuildTools --exact `
                --accept-package-agreements --accept-source-agreements `
                --override "--wait --passive --norestart --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended"
            return ($LASTEXITCODE -eq 0)
        } catch {
            Write-Warning "winget installation failed: $($_.Exception.Message)"
            return $false
        }
    }

    return $false
}

function Write-MsvcInstallInstructions {
    $vsInstall = Get-ExistingVsInstall
    $installPath = if ($vsInstall) {
        $vsInstall.installationPath
    } else {
        "C:\Program Files\Microsoft Visual Studio\2022\Community"
    }

    Write-Host ""
    Write-Host "How to install MSVC (C++ build tools):" -ForegroundColor Yellow
    Write-Host "  Option 1 (Visual Studio Installer GUI):"
    Write-Host "    1. Open 'Visual Studio Installer' from the Start menu."
    Write-Host "    2. Click 'Modify' on your Visual Studio installation."
    Write-Host "    3. Check 'Desktop development with C++' and click 'Modify'."
    Write-Host ""
    Write-Host "  Option 2 (Elevated PowerShell using Visual Studio Installer):"
    Write-Host "    & `"${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\setup.exe`" modify ``"
    Write-Host "      --installPath `"$installPath`" ``"
    Write-Host "      --add Microsoft.VisualStudio.Workload.NativeDesktop ``"
    Write-Host "      --includeRecommended --passive --norestart"
    Write-Host ""
    Write-Host "  Option 3 (winget - standalone Build Tools):"
    Write-Host "    winget install Microsoft.VisualStudio.2022.BuildTools --override `"--wait --passive --norestart --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended`""
    Write-Host ""
}

# Find Visual Studio Developer Environment
$vcvars = Find-VcVars64

if (-not $vcvars) {
    if (Install-Msvc) {
        $vcvars = Find-VcVars64
    }
}

if (-not $vcvars) {
    Write-MsvcInstallInstructions
    Write-Error "Could not find Visual Studio vcvars64.bat. Please install MSVC using the instructions above."
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

