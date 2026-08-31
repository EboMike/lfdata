@echo off
pushd "%~dp0"
powershell -ExecutionPolicy Bypass -File "%~dp0tune-audio.ps1" %*
popd
