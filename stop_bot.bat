@echo off
REM Stop the India News Bot AND the auto-queue daemon.
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process | Where-Object { ($_.Name -eq 'python.exe') -and ($_.CommandLine -like '*main.py*' -or $_.CommandLine -like '*auto_queue.py*') } | ForEach-Object { Write-Host ('stopping PID ' + $_.ProcessId); Stop-Process -Id $_.ProcessId -Force }"
echo Bot and auto-queue stopped (if they were running).
pause
