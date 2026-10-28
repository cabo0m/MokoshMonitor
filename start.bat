@echo off
cd /d "%~dp0"
if not exist config.json copy config.example.json config.json >nul
py -3 -m pip install -r requirements.txt
if errorlevel 1 (pause & exit /b 1)
py -3 monitor.py
if errorlevel 1 pause
