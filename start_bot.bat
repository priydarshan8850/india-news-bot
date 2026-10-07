@echo off
REM Start the India News Bot + auto-queue daemon in the background.
REM Only run this if they are NOT already running (check Task Manager or logs).
cd /d "%~dp0"

if not exist "logs" mkdir logs

start "" "C:\Users\priyd\AppData\Local\Programs\Python\Python313\python.exe" -u main.py 1>> "logs\bot.out.log" 2>> "logs\bot.err.log"
start "" "C:\Users\priyd\AppData\Local\Programs\Python\Python313\python.exe" -u scripts\auto_queue.py 1>> "logs\auto_queue.out.log" 2>> "logs\auto_queue.err.log"

echo Bot + auto-queue started in the background.
echo Live logs: logs\bot.err.log  and  logs\auto_queue.err.log
pause
