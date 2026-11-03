@echo off
setlocal
set PYTHONPATH=%~dp0src
if exist "%~dp0venv\Scripts\python.exe" (
    "%~dp0venv\Scripts\python.exe" -m lflive.tdf_feeder %*
) else (
    python -m lflive.tdf_feeder %*
)
endlocal

