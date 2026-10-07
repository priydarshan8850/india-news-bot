"""Run ONE real cycle right now: collect -> analyze -> publish to Telegram.

Useful for the first live test, for manual posting, or for scheduling with
Windows Task Scheduler instead of keeping main.py running.

Requires `.env` to be configured (bot token + channel + DeepSeek key).

Run:  python scripts/run_once.py      (or double-click run_once.bat)
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
for _noisy in ("httpx", "httpx2", "httpcore"):
    logging.getLogger(_noisy).setLevel(logging.WARNING)  # keep the token out of logs


def main() -> int:
    from config import get_settings
    settings = get_settings()

    if not settings.has_telegram or not settings.telegram_free_channel:
        print(
            "Set TELEGRAM_BOT_TOKEN and TELEGRAM_FREE_CHANNEL in .env first.\n"
            "See README -> 'What you need before the first real run'."
        )
        return 1

    llm_mode = settings.deepseek_model if not settings.use_mock_llm else "MOCK (set DEEPSEEK_API_KEY for real AI summaries)"
    print(f"Channel : {settings.telegram_free_channel}")
    print(f"LLM     : {llm_mode}")
    print("Collecting + analyzing from all sources (the first run takes a few minutes)...\n")

    from pipeline import publish_next, run_collect

    collect_stats = run_collect(settings)
    print("\nCollect:", collect_stats)

    result = publish_next(settings)
    print("Publish:", result)
    if result["published"]:
        print(f"Posted 1 story to {settings.telegram_free_channel} (the 5-min schedule continues when the bot runs).")
    else:
        print("Nothing to post right now (queue empty or daily cap reached).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
