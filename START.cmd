@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\launch.ps1"
if errorlevel 1 (
  echo.
  echo Install Python 3.10+ with Tcl/Tk, then try again.
  echo Or run: python tools\control_panel.py
  pause
)
endlocal
