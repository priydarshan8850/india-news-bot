"""Export already-posted stories to seed_known_posts.json.

Run this on the OLD machine BEFORE moving the bot to a new machine or cloud
(a fresh database), so the channel never repeats stories it already has.
The bot loads this file automatically on every start (idempotent).

Run:  python scripts/export_seed.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    import db

    with db.connect() as conn:
        rows = conn.execute(
            """SELECT title, url FROM articles
               WHERE published_to IS NOT NULL OR premium_published_at IS NOT NULL"""
        ).fetchall()

    data = [{"title": row["title"], "url": row["url"]} for row in rows]
    out = ROOT / "seed_known_posts.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Exported {len(data)} posted stories -> {out.name}")
    print("Ship this file with the project (it is not secret) - the cloud bot")
    print("will load it automatically and never repeat those stories.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
