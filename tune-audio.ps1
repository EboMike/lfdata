$PythonCmd = "python"
$Candidates = @(
    (Join-Path $PSScriptRoot "venv\Scripts\python.exe"),
    (Join-Path $PSScriptRoot ".venv\Scripts\python.exe"),
    "python"
)

foreach ($Path in $Candidates) {
    if ($Path -eq "python" -or (Test-Path $Path)) {
        & $Path -c "import cv2, scipy, numpy, yaml" 2>$null
        if ($LASTEXITCODE -eq 0) {
            $PythonCmd = $Path
            break
        }
    }
}

# Set PYTHONPATH to src folder to ensure local imports work
$env:PYTHONPATH = Join-Path $PSScriptRoot "src"

& $PythonCmd -m lfdata.video.audio_benchmark $args
