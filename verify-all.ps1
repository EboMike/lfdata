# Parameters
param (
    [Parameter(Position = 0, Mandatory = $false)]
    [string]$Directory = "."
)

# Resolve full path to target directory
$TargetDir = Resolve-Path $Directory -ErrorAction SilentlyContinue
if (-not $TargetDir -or -not (Test-Path $TargetDir -PathType Container)) {
    Write-Output "Directory does not exist: $Directory"
    exit 1
}

# Locate Python executable
$PythonPaths = @(
    (Join-Path $PSScriptRoot "venv\Scripts\python.exe"),
    (Join-Path $PSScriptRoot ".venv\Scripts\python.exe")
)

$PythonCmd = "python"
foreach ($Path in $PythonPaths) {
    if (Test-Path $Path) {
        $PythonCmd = $Path
        break
    }
}

# Set PYTHONPATH to src folder to ensure local imports work
$env:PYTHONPATH = Join-Path $PSScriptRoot "src"

& $PythonCmd -m lfdata.verify_all $TargetDir
