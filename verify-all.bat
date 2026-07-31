@echo off
pushd "%~dp0"
powershell -ExecutionPolicy Bypass -File "%~dp0verify-all.ps1" %*
popd
