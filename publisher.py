"""Compose and send Telegram channel posts.

Uses the raw Bot API over httpx, so the pipeline stays synchronous and can be
tested without python-telegram-bot (see ConsolePublisher).
"""
from __future__ import annotations

import html
import json
import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import httpx

from config import Settings

logger = logging.getLogger(__name__)

ORIENTATION_EMOJI = {"neutral": "🟦", "right": "🟧", "left": "🟥", "mixed": "🟪"}
ORIENTATION_LABEL = {
    "neutral": "Neutral",
    "right": "Right-leaning",
    "left": "Left-leaning",
    "mixed": "Mixed",
}
IMPORTANCE_LABEL = {"breaking": "💥 Breaking", "high": "⚡ High", "normal": "🟢 Normal"}
RELIGION_LABEL = {
    "hindu": "Hindu-related",
    "muslim": "Muslim-related",
    "christian": "Christian-related",
    "sikh": "Sikh-related",
    "other": "Religion-related",
}


def _esc(text: str) -> str:
    return html.escape(text or "", quote=False)


def _topics_of(article) -> list[str]:
    try:
        return json.loads(article["topics"] or "[]")
    except (json.JSONDecodeError, TypeError):
        return []


def format_post(article, settings: Settings, premium: bool = False) -> str:
    """article: a sqlite3.Row (or dict) with articles-table columns."""
    title = _esc(article["title"])
    summary = _esc(article["summary_ai"] or article["raw_summary"] or "")
    if len(summary) > 900:
        summary = summary[:897] + "…"

    orientation = article["political_orientation"] or "mixed"
    importance = article["importance"] or "normal"

    chips = [
        f"{ORIENTATION_EMOJI.get(orientation, '🟪')} {ORIENTATION_LABEL.get(orientation, orientation.title())}",
        IMPORTANCE_LABEL.get(importance, "🟢 Normal"),
    ]
    religion = article["religion_topic"]
    if religion:
        chips.append(RELIGION_LABEL.get(religion, religion.title()))

    title_icon = "🎥" if (article["source_type"] or "") == "youtube" else "📰"
    header = "⭐ <b>PREMIUM</b> • 🇮🇳 <b>INDIA NEWS</b>" if premium else "🇮🇳 <b>INDIA NEWS</b>"
    lines = [
        header,
        "",
        f"{title_icon} <b>{title}</b>",
        "",
        " | ".join(chips),
    ]
    topics = _topics_of(article)
    if topics:
        lines.append("🏷 " + " · ".join(t.title() for t in topics[:3]))
    hashtags = " ".join(["#IndiaNews"] + [f"#{t.replace(' ', '').title()}" for t in topics[:3]])
    lines.append(hashtags)

    url = html.escape(article["url"] or "", quote=True)
    source = _esc(article["source"] or "source")
    ist_now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)

    # The channel @handle travels with every forward - free growth.
    handle = settings.telegram_free_channel if settings.telegram_free_channel.startswith("@") else ""
    footer_bits = [part for part in
                   (handle, _esc(settings.footer_text),
                    f"{ist_now.strftime('%d %b %Y, %H:%M')} IST") if part]

    lines += [
        "",
        f"📝 {summary}",
        "",
        f"🔗 Source: <a href=\"{url}\">{source}</a>",
        "",
        f"<i>{' • '.join(footer_bits)}</i>",
    ]
    return "\n".join(lines)[:4000]  # Bot API hard limit is 4096


class ConsolePublisher:
    """Prints posts instead of sending them - used by scripts/dry_run.py."""

    def publish(self, channel: str, text: str) -> int:
        print("=" * 72)
        print(f"CHANNEL: {channel or '(not configured - console fallback)'}")
        print(text)
        print("=" * 72)
        return 0


class TelegramPublisher:
    def __init__(self, token: str, channel: str = ""):
        self._api = f"https://api.telegram.org/bot{token}"
        self._client = httpx.Client(timeout=30)
        self._handle = channel.lstrip("@") if channel.startswith("@") else ""

    def publish(self, channel: str, text: str) -> int:
        resp = self._client.post(
            f"{self._api}/sendMessage",
            json={"chat_id": channel, "text": text, "parse_mode": "HTML"},
        )
        data = resp.json()
        if not data.get("ok"):
            raise RuntimeError(f"Telegram sendMessage failed: {data.get('description')}")
        message_id = int(data["result"]["message_id"])
        # Share buttons point at the public free channel - skip for other channels.
        if self._handle and channel.lstrip("@") == self._handle:
            self._add_share_buttons(message_id)
        return message_id

    def _add_share_buttons(self, message_id: int) -> None:
        """Add Share / Invite buttons - they make every post growth-ready.

        The button needs the post's own link, which exists only after sending,
        so it is added as an immediate edit. Public channels only; failures are
        harmless and logged at debug level.
        """
        if not self._handle:
            return
        post_url = f"https://t.me/{self._handle}/{message_id}"
        share_url = (
            "https://t.me/share/url?url=" + quote(post_url, safe="")
            + "&text=" + quote(f"via @{self._handle}", safe="")
        )
        invite_url = (
            "https://t.me/share/url?url=" + quote(f"https://t.me/{self._handle}", safe="")
            + "&text=" + quote("🇮🇳 24x7 India news — AI summaries, always linked.", safe="")
        )
        try:
            self._client.post(
                f"{self._api}/editMessageReplyMarkup",
                json={
                    "chat_id": f"@{self._handle}",
                    "message_id": message_id,
                    "reply_markup": {"inline_keyboard": [[
                        {"text": "📤 Share", "url": share_url},
                        {"text": "➕ Invite friends", "url": invite_url},
                    ]]},
                },
            )
        except Exception as exc:  # noqa: BLE001 - buttons are a bonus
            logger.debug("Could not add share buttons: %s", exc)


def make_publisher(settings: Settings):
    if settings.has_telegram and settings.telegram_free_channel:
        return TelegramPublisher(settings.telegram_bot_token, channel=settings.telegram_free_channel)
    logger.warning("Telegram not configured - using console publisher (nothing will be sent)")
    return ConsolePublisher()
