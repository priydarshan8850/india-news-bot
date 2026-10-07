@echo off
REM Auto top-up daemon: keeps the GitHub queue stocked with new stories.
REM Start once; it checks every 20 minutes while the PC is on.
REM (start_bot.bat already starts this too - use this file only if you
REM  need the daemon without the bot.)
cd /d "%~dp0"
if not exist "logs" mkdir logs
start "" "C:\Users\priyd\AppData\Local\Programs\Python\Python313\python.exe" -u scripts\auto_queue.py 1>> "logs\auto_queue.out.log" 2>> "logs\auto_queue.err.log"
echo Auto top-up started (every 20 minutes). Log: logs\auto_queue.err.log
pause
