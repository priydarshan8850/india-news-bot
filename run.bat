@echo off
REM India News Bot - first run installs everything, then starts the bot.
REM (.bat is used because PowerShell execution policy blocks unsigned .ps1
REM  scripts on this machine - same workaround as the AIRREV project.)
cd /d "%~dp0"

if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

echo Installing/updating requirements...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements.txt

echo.
echo Starting bot... (Ctrl+C to stop)
".venv\Scripts\python.exe" main.py
pause
