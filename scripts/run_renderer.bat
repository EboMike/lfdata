@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
for %%i in ("%SCRIPT_DIR%..") do set "REPO_ROOT=%%~fi"

set CONFIG=Release
set CONFIG_FILE=

:parse_args
if "%~1"=="" goto after_args
if /i "%~1"=="debug" (
    set CONFIG=Debug
    shift
    goto parse_args
)
if /i "%~1"=="release" (
    set CONFIG=Release
    shift
    goto parse_args
)
if /i "%~1"=="--config" (
    set CONFIG_FILE=%~2
    shift
    shift
    goto parse_args
)
shift
goto parse_args

:after_args
cd /d "%REPO_ROOT%"

set "EXE_PATH=%REPO_ROOT%\build\%CONFIG%\live_renderer.exe"
if not exist "%EXE_PATH%" (
    echo Executable not found at %EXE_PATH%. Building first...
    call "%REPO_ROOT%\scripts\build_renderer.bat" %CONFIG% renderer
    if errorlevel 1 (
        echo Failed to build live_renderer.
        exit /b 1
    )
)

echo Starting live_renderer...
if not "%CONFIG_FILE%"=="" (
    "%EXE_PATH%" --config "%CONFIG_FILE%"
) else (
    "%EXE_PATH%"
)
exit /b %ERRORLEVEL%

