"""Resolve YouTube handles to channel IDs and verify their RSS video feeds.

YouTube offers a keyless RSS feed per channel:
  https://www.youtube.com/feeds/videos.xml?channel_id=UC...

Run:  python scripts/probe_youtube.py [@handle ...]
      (no arguments -> probes the default suggested news channels)
"""
from __future__ import annotations

import re
import sys

import feedparser
import httpx

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; IndiaNewsBot/1.0)"}

DEFAULT_HANDLES = [
    "@aajtak", "@ndtv", "@IndiaToday", "@abpnews", "@RepublicWorld",
    "@WION", "@Firstpost", "@htnewsroom", "@news18india", "@ZeeNews",
    "@DDNewsOfficial", "@livemint",
]

_CHANNEL_ID_RE = re.compile(r'"(?:channelId|externalId)":"(UC[0-9A-Za-z_-]{20,24})"')


def resolve_handle(handle: str) -> str | None:
    handle = handle.strip()
    candidates = [
        f"https://www.youtube.com/{handle}",
        f"https://www.youtube.com/@{handle.lstrip('@')}",
    ]
    for url in candidates:
        try:
            resp = httpx.get(url, headers=HEADERS, timeout=20, follow_redirects=True)
        except Exception:  # noqa: BLE001
            continue
        if resp.status_code != 200:
            continue
        match = _CHANNEL_ID_RE.search(resp.text)
        if match:
            return match.group(1)
    return None


def check_feed(handle: str, channel_id: str) -> None:
    feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    parsed = feedparser.parse(feed_url, agent=HEADERS["User-Agent"])
    if not parsed.entries:
        print(f"{handle:<20} -> {channel_id}  (RSS: NO ENTRIES)")
        return
    channel_name = (parsed.feed.get("title") or "?").strip()
    latest = (parsed.entries[0].get("title") or "")[:70]
    print(f"{handle:<20} -> {channel_id}")
    print(f"{'':<20}    name: {channel_name}")
    print(f"{'':<20}    feed: {len(parsed.entries)} videos | latest: {latest}")
    print(f"{'':<20}    yaml: - name: \"{channel_name}\"\n"
          f"{'':<20}            channel_id: \"{channel_id}\"\n")


if __name__ == "__main__":
    handles = sys.argv[1:] or DEFAULT_HANDLES
    for handle in handles:
        channel_id = resolve_handle(handle)
        if not channel_id:
            print(f"{handle:<20} -> COULD NOT RESOLVE (page blocked or handle gone)")
            continue
        check_feed(handle, channel_id)
