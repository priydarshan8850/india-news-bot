@echo off
REM Start the India News Bot in the background (logs go to logs\bot.err.log).
REM Only run this if the bot is NOT already running (check Task Manager or logs).
cd /d "%~dp0"

if not exist "logs" mkdir logs

start "" "C:\Users\priyd\AppData\Local\Programs\Python\Python313\python.exe" -u main.py 1>> "logs\bot.out.log" 2>> "logs\bot.err.log"

echo Bot started in the background.
echo Live logs: open logs\bot.err.log (or run: type logs\bot.err.log)
pause
