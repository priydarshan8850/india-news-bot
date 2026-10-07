@echo off
REM Stock the cloud queue with every ready story, then ship it to GitHub.
REM GitHub then posts one story every 5 minutes - even when this PC is off.
cd /d "%~dp0"

"C:\Users\priyd\AppData\Local\Programs\Python\Python313\python.exe" scripts\export_queue.py

git add queue/ scripts/ .github/ BATCH_MODE.md push_queue.bat
git commit -m "queue: top up" || echo (nothing new to commit)
git push
pause
