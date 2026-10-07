"""Test RSS feeds: verifies feeds.yaml entries, or URLs passed as arguments.

Run:  python scripts/probe_feeds.py [url1 url2 ...]
      (no arguments -> tests every feed listed in feeds.yaml)
"""
from __future__ import annotations

import sys
from pathlib import Path

import feedparser
import yaml

ROOT = Path(__file__).resolve().parents[1]
FEEDS_FILE = ROOT / "feeds.yaml"
AGENT = "Mozilla/5.0 (compatible; IndiaNewsBot/1.0)"


def test(name: str, url: str) -> None:
    try:
        parsed = feedparser.parse(url, agent=AGENT)
        entries = parsed.entries
        if not entries:
            status = f"NO ENTRIES (bozo={getattr(parsed, 'bozo', 0)})"
        else:
            latest = (entries[0].get("title") or "")[:80]
            status = f"OK: {len(entries)} entries | latest: {latest}"
    except Exception as exc:  # noqa: BLE001
        status = f"ERROR: {exc}"
    print(f"{name}\n    {url}\n    -> {status}\n")


if __name__ == "__main__":
    urls = sys.argv[1:]
    if urls:
        for url in urls:
            test("(candidate)", url)
    else:
        data = yaml.safe_load(FEEDS_FILE.read_text(encoding="utf-8")) or {}
        for feed in data.get("rss") or []:
            test(feed.get("name", "?"), feed.get("url", ""))
