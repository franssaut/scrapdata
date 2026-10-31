@echo off
title Bot Telegram Cipta Group (@Fransscrapcipta_bot)
cd /d "%~dp0"
echo ============================================================
echo   Menjalankan Bot Telegram Cipta Group Official...
echo ============================================================
if exist "%LOCALAPPDATA%\Python\pythoncore-3.15-64\python.exe" (
  set "PY_EXE=%LOCALAPPDATA%\Python\pythoncore-3.15-64\python.exe"
) else (
  set "PY_EXE=python"
)
"%PY_EXE%" -u bot.py
if %ERRORLEVEL% NEQ 0 (
  echo.
  echo [!] Terjadi kendala saat menjalankan bot.
  pause
)
