@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\..\tools\launch.ps1" -LabProfile "%~dp0settings.json"
pause
