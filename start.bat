@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul
where py >nul 2>&1
if errorlevel 1 (
  echo Nie znaleziono Python Launcher. Zainstaluj Python 3.10+ z python.org.
  pause
  exit /b 1
)
if not exist config.json copy config.example.json config.json >nul
if not exist .venv (
  echo Tworze lokalne srodowisko Pythona...
  py -3 -m venv .venv
  if errorlevel 1 (pause & exit /b 1)
)
echo Instaluje wymagane biblioteki...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (pause & exit /b 1)
".venv\Scripts\python.exe" monitor.py
if errorlevel 1 pause
