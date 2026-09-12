# Parameters
param (
    [Parameter(Position = 0, Mandatory = $false)]
    [string]$Path = "."
)

# Resolve full path to target directory or file
$TargetPath = Resolve-Path $Path -ErrorAction SilentlyContinue
if (-not $TargetPath -or -not (Test-Path $TargetPath)) {
    Write-Output "Path does not exist: $Path"
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

& $PythonCmd -m lfdata.verify_all $TargetPath
