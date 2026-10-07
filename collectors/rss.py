"""RSS/Atom feed collector (feedparser)."""
from __future__ import annotations

import calendar
import logging
from datetime import datetime, timezone

import feedparser

from models import RawItem, clean_html

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (compatible; IndiaNewsBot/1.0; personal news aggregator)"


def collect_rss(feeds: list[dict], max_per_feed: int = 15) -> list[RawItem]:
    items: list[RawItem] = []
    for feed in feeds or []:
        url = (feed or {}).get("url")
        name = (feed or {}).get("name") or url
        if not url:
            continue
        try:
            parsed = feedparser.parse(url, agent=USER_AGENT)
        except Exception as exc:  # noqa: BLE001
            logger.warning("RSS feed failed: %s (%s)", name, exc)
            continue
        if getattr(parsed, "bozo", 0) and not parsed.entries:
            logger.warning("RSS feed unreadable (moved or blocked?): %s", name)
            continue

        for entry in parsed.entries[:max_per_feed]:
            link = entry.get("link") or ""
            title = clean_html(entry.get("title") or "")
            if not link or not title:
                continue

            raw_summary = clean_html(entry.get("summary") or "")
            content = raw_summary
            if entry.get("content"):
                try:
                    content = clean_html(entry.content[0].value)
                except (AttributeError, IndexError):
                    pass

            published_at = None
            published = entry.get("published_parsed") or entry.get("updated_parsed")
            if published:
                dt = datetime.fromtimestamp(calendar.timegm(published), tz=timezone.utc)
                published_at = dt.strftime("%Y-%m-%d %H:%M:%S")

            items.append(RawItem(
                url=link,
                title=title,
                summary=raw_summary[:600],
                content=content[:6000],
                source_name=name,
                source_type="rss",
                published_at=published_at,
            ))
    return items
