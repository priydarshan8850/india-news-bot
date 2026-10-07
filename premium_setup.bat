@echo off
REM Create the ₹25/month Telegram Stars subscription link for the premium channel.
REM First: create the private premium channel, add the bot as admin
REM (Post messages + Pin messages + Invite users via link), and set
REM TELEGRAM_PREMIUM_CHANNEL= in .env.
cd /d "%~dp0"

if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

echo Installing/updating requirements...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements.txt

".venv\Scripts\python.exe" scripts\setup_premium.py
pause
