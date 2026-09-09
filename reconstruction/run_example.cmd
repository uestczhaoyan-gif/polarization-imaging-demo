@echo off
cd /d "%~dp0"
set "SCAN_PYTHON=python"
if exist "D:\Anaconda\python.exe" set "SCAN_PYTHON=D:\Anaconda\python.exe"
"%SCAN_PYTHON%" reconstruct.py run --config examples\z_tape\config.json --overwrite --open
pause
