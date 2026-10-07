@echo off
REM Stop the India News Bot AND the auto-queue daemon.
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*india-news-bot*' -and ($_.CommandLine -like '*main.py*' -or $_.CommandLine -like '*auto_queue.py*') } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
echo Bot and auto-queue stopped (if they were running).
pause
