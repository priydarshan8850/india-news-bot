"""Stock the cloud queue: export ready-to-send posts for the GitHub robot.

Run on the PC (or double-click push_queue.bat):
  1. Renders every ready story (analyzed, not yet posted) into a Telegram post.
  2. APPENDS them to queue/posts.json (new stories only - safe to re-run).
  3. Marks them in the local database as queued, so neither the PC bot nor a
     later batch will ever post the same story again.

GitHub then posts one queued story every 5 minutes - even when this PC is off.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

QUEUE_FILE = ROOT / "queue" / "posts.json"
STATE_FILE = ROOT / "queue" / "state.json"
MAX_EXPORT = 400


def main() -> int:
    import db
    from config import get_settings
    from publisher import format_post

    settings = get_settings()
    db.init_db()

    ready = db.select_to_publish(MAX_EXPORT, settings.max_article_age_hours)

    posts: list[dict] = []
    if QUEUE_FILE.exists():
        posts = json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
    known_ids = {entry["id"] for entry in posts}

    added = 0
    for row in ready:
        if row["id"] in known_ids:
            continue
        posts.append({
            "id": row["id"],
            "title": row["title"],
            "url": row["url"],
            "text": format_post(row, settings),
            "queued_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        })
        db.mark_queued_for_github(row["id"])
        added += 1

    QUEUE_FILE.parent.mkdir(exist_ok=True)
    QUEUE_FILE.write_text(json.dumps(posts, ensure_ascii=False, indent=1), encoding="utf-8")
    if not STATE_FILE.exists():
        STATE_FILE.write_text('{"next": 0}', encoding="utf-8")

    sent = json.loads(STATE_FILE.read_text(encoding="utf-8")).get("next", 0)
    print(f"Added {added} new posts. Queue: {len(posts)} total, {sent} already sent.")
    print("Queue file:", QUEUE_FILE)
    print("Next step: push_queue.bat ships it to GitHub (git add/commit/push).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
