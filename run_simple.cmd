@echo off
cd /d "%~dp0"
python reconstruction\simple_reconstruct.py
if errorlevel 1 pause
