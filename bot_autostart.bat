@echo off
REM Auto-start hook for the Windows logon task (no pause - runs hidden).
cd /d "%~dp0"
if not exist "logs" mkdir logs
start "" "C:\Users\priyd\AppData\Local\Programs\Python\Python313\python.exe" -u main.py 1>> "logs\bot.out.log" 2>> "logs\bot.err.log"
start "" "C:\Users\priyd\AppData\Local\Programs\Python\Python313\python.exe" -u scripts\auto_queue.py 1>> "logs\auto_queue.out.log" 2>> "logs\auto_queue.err.log"
