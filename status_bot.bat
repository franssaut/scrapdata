@echo off
title Status Bot Telegram Cipta Group
echo ============================================================
echo   Memeriksa Status Bot Telegram Cipta Group...
echo ============================================================
powershell -Command "$p = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*bot.py*' }; if ($p) { Write-Host '✅ Bot Telegram sedang AKTIF (ONLINE) di background!' -ForegroundColor Green; Write-Host 'PID: ' $p.ProcessId; Write-Host '👉 Chat bot di: https://t.me/Fransscrapcipta_bot' -ForegroundColor Cyan } else { Write-Host '[-] Bot Telegram TIDAK SEDANG BERJALAN (OFFLINE).' -ForegroundColor Yellow; Write-Host '👉 Jalankan start_bot.bat untuk menyalakan bot.' -ForegroundColor White }"
echo ============================================================
pause
