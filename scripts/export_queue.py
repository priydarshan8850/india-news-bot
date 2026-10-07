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
MAX_BUFFER = 288  # unsent stories kept in stock (about 24h of posts at 5-min spacing)


def main() -> int:
    import db
    from config import get_settings
    from publisher import format_post

    settings = get_settings()
    db.init_db()

    posts: list[dict] = []
    if QUEUE_FILE.exists():
        posts = json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
    state = json.loads(STATE_FILE.read_text(encoding="utf-8")) if STATE_FILE.exists() else {"next": 0}
    next_index = int(state.get("next", 0))
    known_ids = {entry["id"] for entry in posts}

    waiting = max(0, len(posts) - next_index)
    room = min(MAX_EXPORT, max(0, MAX_BUFFER - waiting))

    added = 0
    if room > 0:
        for row in db.select_to_publish(room, settings.max_article_age_hours):
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

    print(f"Added {added} new posts. Stock: {waiting + added} waiting, "
          f"{next_index} sent, {len(posts)} total.")
    if room == 0:
        print(f"(Queue buffer full at {MAX_BUFFER} waiting - new stories are added as it drains.)")
    print("Next step: push_queue.bat ships it to GitHub (git add/commit/push).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
