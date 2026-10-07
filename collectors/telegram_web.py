"""Collector for PUBLIC Telegram channels via the t.me/s/<channel> preview.

Read-only, no user account needed. Only works for public channels, and only
for channels that keep the web preview enabled. If a channel blocks the
preview, use Telethon instead (see requirements.txt).
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup

from models import RawItem, clean_html

logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; IndiaNewsBot/1.0)"}
_URL_RE = re.compile(r"https?://\S+")


def _to_sql_utc(value: str | None) -> str | None:
    """'2026-10-04T18:30:17+00:00' -> '2026-10-04 18:30:17' (UTC)."""
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def collect_telegram_channels(channels: list[str], max_per_channel: int = 15) -> list[RawItem]:
    items: list[RawItem] = []
    for channel in channels or []:
        name = str(channel).strip().lstrip("@")
        if not name:
            continue
        page_url = f"https://t.me/s/{name}"
        try:
            resp = httpx.get(page_url, headers=HEADERS, timeout=20, follow_redirects=True)
            resp.raise_for_status()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Telegram channel fetch failed: @%s (%s)", name, exc)
            continue

        soup = BeautifulSoup(resp.text, "html.parser")
        messages = soup.select("div.tgme_widget_message")
        for message in messages[-max_per_channel:]:
            text_el = message.select_one(".tgme_widget_message_text")
            if not text_el:
                continue  # media-only posts are skipped (video is Phase 3)
            text = clean_html(text_el.get_text(" "))
            # Forwarded posts often append short links - drop raw URLs from the
            # body; the post's own t.me link is stored separately.
            text = re.sub(r"\s+", " ", _URL_RE.sub(" ", text)).strip()
            if len(text) < 40:
                continue  # too short to be a news item

            link_el = message.select_one("a.tgme_widget_message_date")
            link = link_el.get("href") if link_el else page_url

            time_el = message.select_one("time[datetime]")
            published_at = _to_sql_utc(time_el.get("datetime") if time_el else None)

            title = text[:140]
            if len(text) > 140:
                title = title.rsplit(" ", 1)[0] + "…"

            items.append(RawItem(
                url=link,
                title=title,
                summary=text[:600],
                content=text[:6000],
                source_name=f"@{name} (Telegram)",
                source_type="telegram",
                published_at=published_at,
            ))
    return items
