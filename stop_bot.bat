@echo off
REM Stop the India News Bot background process.
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*india-news-bot*' -and $_.CommandLine -like '*main.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
echo Bot stopped (if it was running).
pause
