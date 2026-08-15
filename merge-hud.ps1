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

& $PythonCmd -m lfdata.video.hudmerge $args
