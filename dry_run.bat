@echo off
REM Dry run: tests collection + analysis + post formatting offline.
REM Nothing is sent to Telegram and no LLM credits are used.
cd /d "%~dp0"

if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

echo Installing/updating requirements...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements.txt

".venv\Scripts\python.exe" scripts\dry_run.py
pause
