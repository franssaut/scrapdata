@echo off
title PM2 Status - Cipta Group
cd /d "%~dp0"
echo ============================================================
echo   Memeriksa Status PM2...
echo ============================================================
call pm2.cmd status
echo ============================================================
pause
