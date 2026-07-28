@echo off
pushd "%~dp0"
powershell -ExecutionPolicy Bypass -File "%~dp0create-video.ps1" %*
popd
