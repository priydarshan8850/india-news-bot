"""YouTube collector: keyless RSS feed per channel.

Every YouTube channel publishes a public RSS feed:
  https://www.youtube.com/feeds/videos.xml?channel_id=UC...
No API key or quota needed. We post the video title + link only; we do NOT
download the video itself (copyright - see README Phase 3 for permitted video
handling).
"""
from __future__ import annotations

import calendar
import logging
from datetime import datetime, timezone

import feedparser

from models import RawItem, clean_html

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (compatible; IndiaNewsBot/1.0)"


def collect_youtube(channels: list[dict], max_per_channel: int = 5) -> list[RawItem]:
    items: list[RawItem] = []
    for channel in channels or []:
        channel_id = (channel or {}).get("channel_id")
        name = (channel or {}).get("name") or channel_id
        if not channel_id:
            continue

        feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        try:
            parsed = feedparser.parse(feed_url, agent=USER_AGENT)
        except Exception as exc:  # noqa: BLE001
            logger.warning("YouTube feed failed: %s (%s)", name, exc)
            continue
        if not parsed.entries:
            logger.warning("YouTube feed empty or moved: %s", name)
            continue

        for entry in parsed.entries[:max_per_channel]:
            link = entry.get("link") or ""
            title = clean_html(entry.get("title") or "")
            if not link or not title:
                continue

            # feedparser maps <media:description>; fall back to summary.
            description = clean_html(
                getattr(entry, "media_description", None) or entry.get("summary") or ""
            )

            published_at = None
            published = entry.get("published_parsed")
            if published:
                dt = datetime.fromtimestamp(calendar.timegm(published), tz=timezone.utc)
                published_at = dt.strftime("%Y-%m-%d %H:%M:%S")

            items.append(RawItem(
                url=link,
                title=title,
                summary=description[:600],
                content=description[:6000],
                source_name=f"YouTube — {name}",
                source_type="youtube",
                published_at=published_at,
            ))
    return items
