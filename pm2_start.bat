@echo off
title Start PM2 - Bot & Web Cipta Group
cd /d "%~dp0"
echo ============================================================
echo   Menjalankan Bot Telegram ^& Web Server via PM2...
echo ============================================================
call pm2.cmd start ecosystem.config.js
echo.
call pm2.cmd status
echo ============================================================
pause
