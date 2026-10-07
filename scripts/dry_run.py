"""Test the whole pipeline WITHOUT Telegram or an API key.

- collects real items from RSS + Telegram web previews
- uses the offline mock analysis (no DeepSeek calls, no cost)
- prints composed channel posts to the console instead of sending them
- stores everything in dryrun.db (delete it to start fresh)

Run:  python scripts/dry_run.py      (or double-click dry_run.bat)
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Must be set BEFORE config is imported.
os.environ.setdefault("LLM_MOCK", "1")
os.environ.setdefault("DB_PATH", str(ROOT / "dryrun.db"))
os.environ.setdefault("FREE_DAILY_CAP", "3")
os.environ.setdefault("MAX_ARTICLES_PER_FEED", "8")

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
for _noisy in ("httpx", "httpx2", "httpcore"):
    logging.getLogger(_noisy).setLevel(logging.WARNING)


def main() -> int:
    from config import get_settings
    from pipeline import run_cycle
    from publisher import ConsolePublisher

    settings = get_settings()
    print(f"Feeds: {settings.feeds_path}")
    print(f"DB:    {settings.db_path}")
    print(f"LLM:   {'mock (offline heuristics)' if settings.use_mock_llm else 'live'}")
    print("Running one full cycle...\n")

    stats = run_cycle(settings, ConsolePublisher(), publish_limit=3)

    print("\nCycle stats:", stats)
    print("\nThis was a dry run - nothing was sent to Telegram and no LLM credits were used.")
    print("Delete dryrun.db to reset the test state.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
