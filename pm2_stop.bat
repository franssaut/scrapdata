@echo off
title Stop PM2 - Cipta Group
cd /d "%~dp0"
echo ============================================================
echo   Menghentikan Bot Telegram ^& Web Server di PM2...
echo ============================================================
call pm2.cmd stop all
call pm2.cmd delete all
echo ============================================================
echo   Semua proses PM2 berhasil dihentikan.
echo ============================================================
pause
