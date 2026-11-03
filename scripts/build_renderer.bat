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
cd /d "%REPO_ROOT%"

if "%CLEAN%"=="1" (
    echo Cleaning build directory...
    if exist "%REPO_ROOT%\build" rd /s /q "%REPO_ROOT%\build"
)

set VCVARS=
if exist "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat" (
    set "VCVARS=C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat"
) else if exist "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" (
    set "VCVARS=C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"
) else if exist "C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\VC\Auxiliary\Build\vcvars64.bat" (
    set "VCVARS=C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\VC\Auxiliary\Build\vcvars64.bat"
)

if "%VCVARS%"=="" (
    echo Error: Could not find Visual Studio vcvars64.bat.
    exit /b 1
)

echo Initializing MSVC and building live_renderer (%CONFIG%, target: %TARGET%)...
call "%VCVARS%"
cd /d "%REPO_ROOT%"
if errorlevel 1 exit /b 1

cmake -B "%REPO_ROOT%\build" -S "%REPO_ROOT%\src\live_renderer" -DYAML_MSVC_SHARED_RT=ON
if errorlevel 1 exit /b 1

if "%TARGET%"=="all" (
    cmake --build "%REPO_ROOT%\build" --config %CONFIG%
) else (
    cmake --build "%REPO_ROOT%\build" --config %CONFIG% --target %TARGET%
)

if errorlevel 1 (
    echo Build failed.
    exit /b 1
)

echo Build succeeded.
exit /b 0

