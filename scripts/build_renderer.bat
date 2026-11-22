@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
for %%i in ("%SCRIPT_DIR%..") do set "REPO_ROOT=%%~fi"

set CONFIG=Release
set TARGET=all
set CLEAN=0

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
if /i "%~1"=="clean" (
    set CLEAN=1
    shift
    goto parse_args
)
if /i "%~1"=="tests" (
    set TARGET=live_renderer_tests
    shift
    goto parse_args
)
if /i "%~1"=="renderer" (
    set TARGET=live_renderer
    shift
    goto parse_args
)
shift
goto parse_args

:after_args
set "CLEAN_ARG="
if "%CLEAN%"=="1" set "CLEAN_ARG=-Clean"

powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%build_renderer.ps1" -Config %CONFIG% -Target %TARGET% %CLEAN_ARG%
exit /b %errorlevel%

