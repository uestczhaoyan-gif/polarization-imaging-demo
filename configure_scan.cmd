@echo off
cd /d "%~dp0"
set "SCAN_PYTHON=python"
if exist "D:\Anaconda\python.exe" set "SCAN_PYTHON=D:\Anaconda\python.exe"
"%SCAN_PYTHON%" reconstruct.py wizard --output local\config.json
pause
