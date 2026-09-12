@echo off
pushd "%~dp0"
powershell -ExecutionPolicy Bypass -File "%~dp0dump-tdf.ps1" %*
popd
