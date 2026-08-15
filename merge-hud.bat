@echo off
pushd "%~dp0"
powershell -ExecutionPolicy Bypass -File "%~dp0merge-hud.ps1" %*
popd
