"""Send a premium digest right now (manual test / catch-up).

Run:  python scripts/send_digest.py
Requires TELEGRAM_PREMIUM_CHANNEL in .env (see premium_setup.bat).
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

    if not settings.telegram_premium_channel:
        print("TELEGRAM_PREMIUM_CHANNEL is not set in .env.\n"
              "Create the premium channel, add the bot as admin, then set it - "
              "see README Phase 2 / SETUP_GUIDE Part G.")
        return 1

    from digest import build_digest, send_digest

    preview = build_digest(settings)
    if not preview:
        print("No recent stories available for a digest yet.")
        return 0
    print("Digest preview:\n")
    print(preview)
    print()

    if send_digest(settings):
        print(f"Digest sent to {settings.telegram_premium_channel}")
    else:
        print("Nothing to send.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
