@echo off
title PM2 Logs - Cipta Group
cd /d "%~dp0"
echo ============================================================
echo   Menampilkan Log PM2 Bot Telegram...
echo ============================================================
call pm2.cmd logs cipta-bot --lines 50
pause
