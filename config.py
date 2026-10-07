"""Central configuration for the India News Telegram bot.

Every value comes from environment variables (see `.env.example`).
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _env_int(name: str, default: int) -> int:
    try:
        return int(_env(name) or default)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(_env(name) or default)
    except ValueError:
        return default


def _env_bool(name: str, default: bool = False) -> bool:
    raw = _env(name).lower()
    if raw in ("1", "true", "yes", "on"):
        return True
    if raw in ("0", "false", "no", "off"):
        return False
    return default


@dataclass(frozen=True)
class Settings:
    # --- Telegram ---
    telegram_bot_token: str
    telegram_free_channel: str        # "@channelname" or "-100..."
    telegram_premium_channel: str     # optional, "" when unused
    admin_user_id: int                # 0 = no admin commands

    # --- LLM (DeepSeek / any OpenAI-compatible endpoint) ---
    deepseek_api_key: str
    deepseek_base_url: str
    deepseek_model: str
    llm_mock: bool                    # True -> offline heuristic analysis
    summary_language: str             # "en" | "hi" | "both"

    # --- Behaviour ---
    collect_interval_minutes: int
    publish_interval_minutes: int
    free_daily_cap: int
    max_articles_per_feed: int
    dedupe_window_hours: int
    dedupe_threshold: float
    max_article_age_hours: int

    # --- Premium tier (exclusive content, Telegram Stars subscriptions) ---
    premium_price_stars: int
    premium_invite_link: str
    premium_publish_interval_minutes: int
    premium_publish_batch: int

    # --- Files / optional integrations ---
    db_path: Path
    feeds_path: Path
    x_bearer_token: str
    footer_text: str
    log_level: str

    @property
    def has_telegram(self) -> bool:
        return bool(self.telegram_bot_token)

    @property
    def use_mock_llm(self) -> bool:
        """Mock when explicitly asked for, or when there is no API key."""
        return self.llm_mock or not self.deepseek_api_key


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    db_path = Path(_env("DB_PATH") or (BASE_DIR / "newsbot.db"))
    feeds_path = Path(_env("FEEDS_FILE") or (BASE_DIR / "feeds.yaml"))
    return Settings(
        telegram_bot_token=_env("TELEGRAM_BOT_TOKEN"),
        telegram_free_channel=_env("TELEGRAM_FREE_CHANNEL"),
        telegram_premium_channel=_env("TELEGRAM_PREMIUM_CHANNEL"),
        admin_user_id=_env_int("ADMIN_USER_ID", 0),
        deepseek_api_key=_env("DEEPSEEK_API_KEY"),
        deepseek_base_url=_env("DEEPSEEK_BASE_URL") or "https://api.deepseek.com",
        deepseek_model=_env("DEEPSEEK_MODEL") or "deepseek-chat",
        llm_mock=_env_bool("LLM_MOCK", False),
        summary_language=(_env("SUMMARY_LANGUAGE") or "en").lower(),
        collect_interval_minutes=_env_int("COLLECT_INTERVAL_MINUTES", 15),
        publish_interval_minutes=_env_int("PUBLISH_INTERVAL_MINUTES", 5),
        free_daily_cap=_env_int("FREE_DAILY_CAP", 300),
        max_articles_per_feed=_env_int("MAX_ARTICLES_PER_FEED", 15),
        dedupe_window_hours=_env_int("DEDUPE_WINDOW_HOURS", 72),
        dedupe_threshold=_env_float("DEDUPE_THRESHOLD", 0.87),
        max_article_age_hours=_env_int("MAX_ARTICLE_AGE_HOURS", 48),
        premium_price_stars=_env_int("PREMIUM_PRICE_STARS", 15),
        premium_invite_link=_env("PREMIUM_INVITE_LINK"),
        premium_publish_interval_minutes=_env_int("PREMIUM_PUBLISH_INTERVAL_MINUTES", 5),
        premium_publish_batch=_env_int("PREMIUM_PUBLISH_BATCH", 5),
        db_path=db_path,
        feeds_path=feeds_path,
        x_bearer_token=_env("X_BEARER_TOKEN"),
        footer_text=_env("POST_FOOTER") or "Published automatically by IndiaNewsBot",
        log_level=(_env("LOG_LEVEL") or "INFO").upper(),
    )
