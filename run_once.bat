@echo off
REM Run ONE real cycle right now (collect -> analyze -> publish).
REM Requires .env to be configured. Creates .venv on first use.
cd /d "%~dp0"

if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

echo Installing/updating requirements...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements.txt

".venv\Scripts\python.exe" scripts\run_once.py
pause
