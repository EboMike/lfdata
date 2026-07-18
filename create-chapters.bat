@echo off
pushd "%~dp0"
powershell -ExecutionPolicy Bypass -File "%~dp0create-chapters.ps1" %*
popd
