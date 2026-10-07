"""SQLite storage: articles, analysis results, publishing state.

All timestamps are stored as "YYYY-MM-DD HH:MM:SS" UTC so SQLite's date
functions compare them correctly (see `utc_now_sql`).
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator

from config import get_settings
from dedupe import normalize_title, url_hash
from models import RawItem


def utc_now_sql() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    url                   TEXT NOT NULL,
    url_hash              TEXT NOT NULL UNIQUE,
    title                 TEXT NOT NULL,
    title_norm            TEXT,
    source                TEXT,
    source_type           TEXT,
    raw_summary           TEXT,
    content               TEXT,
    published_at          TEXT,
    collected_at          TEXT NOT NULL,
    status                TEXT NOT NULL DEFAULT 'new',
    dup_of                INTEGER,
    political_orientation TEXT,
    topics                TEXT,
    religion_topic        TEXT,
    importance            TEXT,
    summary_ai            TEXT,
    llm_confidence        REAL,
    published_to          TEXT,
    message_id            INTEGER,
    published_at_bot      TEXT,
    premium_message_id    INTEGER,
    premium_published_at  TEXT
);
CREATE INDEX IF NOT EXISTS idx_articles_status ON articles(status);
CREATE INDEX IF NOT EXISTS idx_articles_collected ON articles(collected_at);
CREATE TABLE IF NOT EXISTS state (
    key   TEXT PRIMARY KEY,
    value TEXT
);
"""


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    settings = get_settings()
    conn = sqlite3.connect(settings.db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)
        # Migration for databases created before the premium tier existed.
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(articles)")}
        if "premium_message_id" not in columns:
            conn.execute("ALTER TABLE articles ADD COLUMN premium_message_id INTEGER")
        if "premium_published_at" not in columns:
            conn.execute("ALTER TABLE articles ADD COLUMN premium_published_at TEXT")


# ---------------------------------------------------------------------------
# Insert / dedupe
# ---------------------------------------------------------------------------

def insert_new_article(item: RawItem) -> tuple[int, bool]:
    """Insert if this URL was not seen before. Returns (row id, was_new)."""
    digest = url_hash(item.url)
    with connect() as conn:
        cur = conn.execute(
            """INSERT OR IGNORE INTO articles
               (url, url_hash, title, title_norm, source, source_type,
                raw_summary, content, published_at, collected_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                item.url, digest, item.title, normalize_title(item.title),
                item.source_name, item.source_type, item.summary, item.content,
                item.published_at, utc_now_sql(),
            ),
        )
        if cur.rowcount == 1:
            return int(cur.lastrowid), True
        row = conn.execute("SELECT id FROM articles WHERE url_hash = ?", (digest,)).fetchone()
        return (int(row["id"]) if row else 0), False


def recent_titles(hours: int) -> list[sqlite3.Row]:
    """[(id, title_norm), ...] for fuzzy duplicate checking."""
    with connect() as conn:
        return conn.execute(
            """SELECT id, title_norm FROM articles
               WHERE collected_at >= datetime('now', ?)
               ORDER BY id DESC LIMIT 800""",
            (f"-{int(hours)} hours",),
        ).fetchall()


def pending_new(limit: int = 200) -> list[sqlite3.Row]:
    """Articles an interrupted run inserted but never finished analyzing."""
    with connect() as conn:
        return conn.execute(
            "SELECT * FROM articles WHERE status = 'new' ORDER BY id LIMIT ?",
            (int(limit),),
        ).fetchall()


def mark_duplicate(article_id: int, dup_of: int) -> None:
    with connect() as conn:
        conn.execute(
            "UPDATE articles SET status = 'duplicate', dup_of = ? WHERE id = ?",
            (dup_of, article_id),
        )


def mark_failed(article_id: int) -> None:
    with connect() as conn:
        conn.execute("UPDATE articles SET status = 'failed' WHERE id = ?", (article_id,))


def save_analysis(article_id: int, analysis: dict) -> None:
    with connect() as conn:
        conn.execute(
            """UPDATE articles SET
                   status = 'processed',
                   political_orientation = ?,
                   topics = ?,
                   religion_topic = ?,
                   importance = ?,
                   summary_ai = ?,
                   llm_confidence = ?
               WHERE id = ?""",
            (
                analysis["political_orientation"],
                json.dumps(analysis["topics"], ensure_ascii=False),
                analysis["religion_topic"],
                analysis["importance"],
                analysis["summary"],
                analysis["confidence"],
                article_id,
            ),
        )


# ---------------------------------------------------------------------------
# Publishing
# ---------------------------------------------------------------------------

def select_to_publish(limit: int, max_age_hours: int) -> list[sqlite3.Row]:
    """Unpublished processed stories, breaking/high first, then newest."""
    with connect() as conn:
        return conn.execute(
            """SELECT * FROM articles
               WHERE status = 'processed' AND published_to IS NULL
                 AND COALESCE(published_at, collected_at) >= datetime('now', ?)
               ORDER BY CASE importance
                            WHEN 'breaking' THEN 0
                            WHEN 'high' THEN 1
                            ELSE 2
                        END,
                        COALESCE(published_at, collected_at) DESC
               LIMIT ?""",
            (f"-{int(max_age_hours)} hours", int(limit)),
        ).fetchall()


def published_last_24h() -> int:
    with connect() as conn:
        row = conn.execute(
            """SELECT COUNT(*) AS n FROM articles
               WHERE published_at_bot >= datetime('now', '-24 hours')"""
        ).fetchone()
        return int(row["n"])


def mark_published(article_id: int, channel: str, message_id: int) -> None:
    with connect() as conn:
        conn.execute(
            """UPDATE articles SET
                   status = 'published', published_to = ?, message_id = ?,
                   published_at_bot = ?
               WHERE id = ?""",
            (channel, message_id, utc_now_sql(), article_id),
        )


def mark_queued_for_github(article_id: int) -> None:
    """Exported to the GitHub queue: counts as posted so nothing repeats.

    The GitHub robot will actually deliver it; we mark it now so the local bot
    skips it, the daily cap accounts for it, and same-event suppression works.
    """
    with connect() as conn:
        conn.execute(
            """UPDATE articles SET
                   status = 'published', published_to = 'github-queue',
                   published_at_bot = ?
               WHERE id = ?""",
            (utc_now_sql(), article_id),
        )


def latest_published(limit: int = 8) -> list[sqlite3.Row]:
    with connect() as conn:
        return conn.execute(
            """SELECT title, url, source, importance, summary_ai, published_at_bot
               FROM articles
               WHERE published_to IS NOT NULL
               ORDER BY published_at_bot DESC
               LIMIT ?""",
            (int(limit),),
        ).fetchall()


def recent_published_titles(hours: int = 48) -> list[sqlite3.Row]:
    """Everything published in the last N hours - the repeat-suppression base."""
    with connect() as conn:
        return conn.execute(
            """SELECT id, title_norm, title FROM articles
               WHERE published_to IS NOT NULL
                 AND published_at_bot >= datetime('now', ?)
               ORDER BY published_at_bot DESC LIMIT 400""",
            (f"-{int(hours)} hours",),
        ).fetchall()


def recent_premium_titles(hours: int = 48) -> list[sqlite3.Row]:
    """Stories already posted to the PREMIUM channel (repeat base)."""
    with connect() as conn:
        return conn.execute(
            """SELECT id, title_norm FROM articles
               WHERE premium_published_at >= datetime('now', ?)
               ORDER BY premium_published_at DESC LIMIT 400""",
            (f"-{int(hours)} hours",),
        ).fetchall()


def select_to_publish_premium(limit: int, max_age_hours: int) -> list[sqlite3.Row]:
    """Analyzed stories not yet sent to premium - the COMPLETE feed."""
    with connect() as conn:
        return conn.execute(
            """SELECT * FROM articles
               WHERE summary_ai IS NOT NULL AND premium_published_at IS NULL
                 AND COALESCE(published_at, collected_at) >= datetime('now', ?)
               ORDER BY CASE importance
                            WHEN 'breaking' THEN 0
                            WHEN 'high' THEN 1
                            ELSE 2
                        END,
                        COALESCE(published_at, collected_at) DESC
               LIMIT ?""",
            (f"-{int(max_age_hours)} hours", int(limit)),
        ).fetchall()


def mark_premium_published(article_id: int, channel: str, message_id: int) -> None:
    with connect() as conn:
        conn.execute(
            """UPDATE articles SET premium_message_id = ?, premium_published_at = ?
               WHERE id = ?""",
            (message_id, utc_now_sql(), article_id),
        )


def load_seed_posts(payload: list[dict]) -> int:
    """Insert already-posted stories as 'published' rows (idempotent).

    Used when migrating to a fresh machine/volume, so the channel never
    repeats a story that the previous machine already posted.
    """
    inserted = 0
    now = utc_now_sql()
    with connect() as conn:
        for entry in payload:
            title = str((entry or {}).get("title") or "").strip()
            url = str((entry or {}).get("url") or "").strip()
            if not title or not url:
                continue
            cur = conn.execute(
                """INSERT OR IGNORE INTO articles
                   (url, url_hash, title, title_norm, source, source_type,
                    collected_at, status, published_to, published_at_bot)
                   VALUES (?, ?, ?, ?, '(seed)', 'seed', ?, 'published', 'seed', ?)""",
                (url, url_hash(url), title, normalize_title(title), now, now),
            )
            inserted += cur.rowcount
    return inserted


def digest_candidates(hours: int = 12, limit: int = 36) -> list[sqlite3.Row]:
    """Best analyzed stories of the recent past - premium digest material."""
    with connect() as conn:
        return conn.execute(
            """SELECT id, title, title_norm, url FROM articles
               WHERE summary_ai IS NOT NULL
                 AND COALESCE(published_at, collected_at) >= datetime('now', ?)
               ORDER BY CASE importance
                            WHEN 'breaking' THEN 0
                            WHEN 'high' THEN 1
                            ELSE 2
                        END,
                        COALESCE(published_at, collected_at) DESC
               LIMIT ?""",
            (f"-{int(hours)} hours", int(limit)),
        ).fetchall()


def stats() -> dict:
    with connect() as conn:
        total = int(conn.execute("SELECT COUNT(*) AS n FROM articles").fetchone()["n"])
        by_status = {
            row["status"]: int(row["n"])
            for row in conn.execute("SELECT status, COUNT(*) AS n FROM articles GROUP BY status")
        }
        published_24h = int(conn.execute(
            """SELECT COUNT(*) AS n FROM articles
               WHERE published_at_bot >= datetime('now', '-24 hours')"""
        ).fetchone()["n"])
        premium_24h = int(conn.execute(
            """SELECT COUNT(*) AS n FROM articles
               WHERE premium_published_at >= datetime('now', '-24 hours')"""
        ).fetchone()["n"])
        state_row = conn.execute(
            "SELECT value FROM state WHERE key = 'last_cycle_at'"
        ).fetchone()
    out = {"total": total, "published_24h": published_24h, "premium_24h": premium_24h}
    out.update(by_status)
    out["last_cycle_at"] = state_row["value"] if state_row else "never"
    return out


# ---------------------------------------------------------------------------
# Key/value state
# ---------------------------------------------------------------------------

def get_state(key: str, default: str = "") -> str:
    with connect() as conn:
        row = conn.execute("SELECT value FROM state WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default


def set_state(key: str, value: str) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO state (key, value) VALUES (?, ?)", (key, value)
        )
