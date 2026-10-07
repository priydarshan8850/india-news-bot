"""Exclusive daily digest for the premium channel.

Assembled from stories that are already analyzed (no extra LLM cost): the
day's most important stories in one post, with links. Sent by the bot at
08:00 and 20:00 IST, or manually via scripts/send_digest.py.
"""
from __future__ import annotations

import html
import logging
from datetime import datetime, timedelta, timezone

import db
from config import Settings, get_settings
from dedupe import normalize_title, same_event
from publisher import make_publisher

logger = logging.getLogger(__name__)

IST = timezone(timedelta(hours=5, minutes=30))


def build_digest(settings: Settings | None = None, hours: int = 12, limit: int = 12) -> str | None:
    """Compose the digest text, or None when there is nothing to include."""
    settings = settings or get_settings()
    rows = db.digest_candidates(hours=hours, limit=limit * 3)

    picked: list = []
    norms: list[str] = []
    for row in rows:
        norm = row["title_norm"] or normalize_title(row["title"])
        if any(same_event(norm, other) for other in norms):
            continue  # the same event twice would make the digest look broken
        norms.append(norm)
        picked.append(row)
        if len(picked) >= limit:
            break

    if not picked:
        return None

    now_ist = datetime.now(IST)
    part = "Morning" if now_ist.hour < 15 else "Evening"
    lines = [
        f"🗞 <b>{part} DIGEST</b> • {now_ist.strftime('%d %b %Y')}",
        "<i>Exclusive roundup for premium members</i>",
        "",
    ]
    for row in picked:
        title = html.escape(row["title"], quote=False)
        url = html.escape(row["url"] or "", quote=True)
        lines.append(f'• <a href="{url}">{title}</a>')
    lines += [
        "",
        "<i>⭐ Premium by IndiaNewsBot — full feed, no repeats</i>",
    ]
    return "\n".join(lines)[:4000]


def send_digest(settings: Settings | None = None, publisher=None) -> bool:
    """Build and send the digest to the premium channel. False if impossible."""
    settings = settings or get_settings()
    if not settings.telegram_premium_channel:
        return False
    text = build_digest(settings)
    if not text:
        return False
    publisher = publisher or make_publisher(settings)
    publisher.publish(settings.telegram_premium_channel, text)
    logger.info("Digest sent to premium channel")
    return True
