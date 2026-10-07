"""Collectors package: RSS, YouTube, Telegram public channels, optional X API.

Submodules are imported lazily inside `collect_all` so that a missing optional
dependency (e.g. beautifulsoup4) only disables that one collector instead of
breaking the whole application.
"""
from __future__ import annotations

import logging

import yaml

from config import Settings
from models import RawItem

logger = logging.getLogger(__name__)


def load_feeds(settings: Settings) -> dict:
    """Read feeds.yaml -> {"rss": [...], "telegram_channels": [...], "x_accounts": [...]}"""
    if not settings.feeds_path.exists():
        logger.warning("Feeds file not found: %s", settings.feeds_path)
        return {}
    with open(settings.feeds_path, encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def collect_all(settings: Settings) -> list[RawItem]:
    config = load_feeds(settings)
    items: list[RawItem] = []

    try:
        from collectors.rss import collect_rss
        rss_items = collect_rss(config.get("rss") or [], settings.max_articles_per_feed)
        items.extend(rss_items)
    except Exception as exc:  # noqa: BLE001 - one broken collector must not kill the cycle
        logger.error("RSS collection failed: %s", exc)

    try:
        from collectors.telegram_web import collect_telegram_channels
        tg_items = collect_telegram_channels(config.get("telegram_channels") or [])
        items.extend(tg_items)
    except Exception as exc:  # noqa: BLE001
        logger.error("Telegram collection failed: %s", exc)

    try:
        from collectors.youtube import collect_youtube
        yt_items = collect_youtube(config.get("youtube_channels") or [])
        items.extend(yt_items)
    except Exception as exc:  # noqa: BLE001
        logger.error("YouTube collection failed: %s", exc)

    if settings.x_bearer_token:
        try:
            from collectors.x_api import collect_x
            x_items = collect_x(config.get("x_accounts") or [], settings.x_bearer_token)
            items.extend(x_items)
        except Exception as exc:  # noqa: BLE001
            logger.error("X collection failed: %s", exc)

    logger.info(
        "Collected %d items (rss=%d, youtube=%d, telegram=%d, x=%d)",
        len(items),
        sum(1 for i in items if i.source_type == "rss"),
        sum(1 for i in items if i.source_type == "youtube"),
        sum(1 for i in items if i.source_type == "telegram"),
        sum(1 for i in items if i.source_type == "x"),
    )
    return items
