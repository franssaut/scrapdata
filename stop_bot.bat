@echo off
title Stop Bot Telegram Cipta Group
echo ============================================================
echo   Menghentikan Bot Telegram Cipta Group...
echo ============================================================
powershell -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*bot.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue; Write-Host 'Menghentikan proses bot ID: ' $_.ProcessId }"
echo ============================================================
echo Bot berhasil dihentikan.
echo ============================================================
pause
