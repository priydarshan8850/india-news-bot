"""Auto top-up: keeps the GitHub queue stocked with new news while the PC is on.

Every AUTOQUEUE_INTERVAL_MINUTES (default 20) it runs the exporter and, when
new stories were added, commits and pushes them to GitHub. GitHub then keeps
posting to Telegram every 5 minutes - so you rarely need push_queue.bat by hand.

Run in the background:  auto_queue.bat
Stop both bot + this daemon:  stop_bot.bat
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
EXPORT = ROOT / "scripts" / "export_queue.py"
INTERVAL = max(5, int(os.environ.get("AUTOQUEUE_INTERVAL_MINUTES", "20"))) * 60


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=180
    )
    if check and result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {result.stderr.strip()[:300]}")
    return result


def cycle() -> None:
    stamp = time.strftime("%H:%M:%S")
    export = subprocess.run(
        [PY, str(EXPORT)], cwd=ROOT, capture_output=True, text=True, timeout=900
    )
    summary = (export.stdout or export.stderr or "").strip().replace("\n", " | ")
    print(f"[{stamp}] export: {summary}")

    if "Added 0 new posts" in (export.stdout or ""):
        return  # buffer fine, nothing to push

    try:
        git("pull", "--rebase", "--autostash")
    except Exception as exc:  # noqa: BLE001
        print(f"    git pull failed, retrying next cycle: {exc}")
        return

    git("add", "queue/")
    commit = git("commit", "-m", "queue: auto top-up", check=False)
    if commit.returncode != 0:
        print("    nothing new to commit")
        return

    for attempt in range(2):
        push = git("push", check=False)
        if push.returncode == 0:
            print("    pushed to GitHub - the cloud robot will post these too")
            return
        print(f"    push failed (attempt {attempt + 1}): {push.stderr.strip()[:200]}")
        git("pull", "--rebase", "--autostash", check=False)
    print("    push gave up for now - next cycle retries")


def main() -> int:
    print(f"Auto top-up running (every {INTERVAL // 60} min). Stop with stop_bot.bat.")
    while True:
        try:
            cycle()
        except Exception as exc:  # noqa: BLE001 - the daemon must never die
            print(f"cycle error: {exc}")
        time.sleep(INTERVAL)


if __name__ == "__main__":
    sys.exit(main())
