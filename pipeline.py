"""Pipeline steps: collect -> dedupe -> analyze -> store, then paced publish.

- run_collect():  pulls every source, dedupes and analyzes new articles.
- publish_next(): publishes AT MOST ONE story per call (the bot calls it on a
  timer, e.g. every 5 minutes) after a second same-event duplicate check
  against everything already on the channel.
- run_cycle():    convenience = run_collect + a few publish_next calls.
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

import db
import llm
from collectors import collect_all
from config import Settings, get_settings
from dedupe import find_duplicate, normalize_title, same_event
from models import RawItem
from publisher import format_post, make_publisher

logger = logging.getLogger(__name__)

# Pause between posts when several are published in a row (dry runs/catch-up).
_PUBLISH_PAUSE_SECONDS = 1.2

_STAT_TO_STATS = {"duplicate": "duplicates", "analyzed": "analyzed", "failed": "failed"}


def _row_as_item(row) -> RawItem:
    """Rebuild a RawItem from a stored article row (backlog recovery)."""
    return RawItem(
        url=row["url"],
        title=row["title"],
        summary=row["raw_summary"] or "",
        content=row["content"] or "",
        source_name=row["source"] or "",
        source_type=row["source_type"] or "rss",
        published_at=row["published_at"],
    )


def _analyze_one(article_id, item, recent, settings, exclude_self: bool = False) -> str:
    """Dedupe + LLM-analyze one article. Returns duplicate | analyzed | failed."""
    norm = normalize_title(item.title)
    compare = recent
    if exclude_self:  # backlog rows are already in `recent` - don't match self
        compare = [(rid, rnorm) for rid, rnorm in recent if rid != article_id]
    dup_of = find_duplicate(norm, compare, settings.dedupe_threshold)
    if dup_of:
        db.mark_duplicate(article_id, dup_of)
        return "duplicate"
    try:
        analysis = llm.analyze(item, settings)
    except llm.LLMError as exc:
        logger.error("Analysis failed for %s: %s", item.url, exc)
        db.mark_failed(article_id)
        return "failed"
    if not analysis.get("summary"):
        analysis["summary"] = (item.summary or item.content or item.title)[:400]
    db.save_analysis(article_id, analysis)
    recent.append((article_id, norm))  # later items/batches can match it
    return "analyzed"


def run_collect(settings: Settings | None = None) -> dict:
    """Collect from every source, dedupe and analyze new articles."""
    settings = settings or get_settings()
    db.init_db()

    # Carry over posting history when running on a fresh machine/volume, so the
    # channel never repeats a story posted by a previous machine. Idempotent.
    seed_file = settings.db_path.parent / "seed_known_posts.json"
    if not seed_file.exists():
        seed_file = Path(__file__).resolve().parent / "seed_known_posts.json"
    if seed_file.exists():
        try:
            seeded = db.load_seed_posts(json.loads(seed_file.read_text(encoding="utf-8")))
            if seeded:
                logger.info("Loaded %d known-published stories from %s", seeded, seed_file.name)
        except Exception as exc:  # noqa: BLE001 - seeding must never break collection
            logger.warning("Could not load seed file: %s", exc)

    stats = {
        "collected": 0, "new": 0, "duplicates": 0,
        "analyzed": 0, "failed": 0, "recovered": 0,
    }

    # 1. Collect -------------------------------------------------------------
    items = collect_all(settings)
    stats["collected"] = len(items)

    # 2. Store new URLs ------------------------------------------------------
    # Snapshot recent titles BEFORE inserting this batch: otherwise every new
    # article would match its own freshly-inserted row as a "duplicate".
    recent = [(row["id"], row["title_norm"]) for row in db.recent_titles(settings.dedupe_window_hours)]

    new_rows: list[tuple[int, object]] = []
    for item in items:
        if not item.url or not item.title:
            continue
        article_id, was_new = db.insert_new_article(item)
        if was_new:
            new_rows.append((article_id, item))
    stats["new"] = len(new_rows)

    # 3. Dedupe + analyze ------------------------------------------------------
    for article_id, item in new_rows:
        outcome = _analyze_one(article_id, item, recent, settings)
        stats[_STAT_TO_STATS[outcome]] += 1
        if outcome == "duplicate":
            logger.info("Duplicate skipped: %s", item.title[:80])

    # 3b. Retry articles an interrupted earlier run never finished analyzing.
    for row in db.pending_new(200):
        item = _row_as_item(row)
        outcome = _analyze_one(row["id"], item, recent, settings, exclude_self=True)
        if outcome == "analyzed":
            stats["recovered"] += 1
            logger.info("Recovered pending article: %s", item.title[:80])
        else:
            stats[_STAT_TO_STATS[outcome]] += 1

    db.set_state("last_cycle_at", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))
    logger.info("Collect done: %s", stats)
    return stats


def publish_next(settings: Settings | None = None, publisher=None) -> dict:
    """Publish the single best pending story, if any.

    Candidates are checked against everything published in the last 48h
    (exact, fuzzy and same-event matching) so a story never repeats on the
    channel; same-event candidates are marked as duplicates and skipped.
    """
    settings = settings or get_settings()
    publisher = publisher or make_publisher(settings)
    db.init_db()

    result = {"published": 0, "duplicates": 0, "cap_reached": False}

    remaining_cap = settings.free_daily_cap - db.published_last_24h()
    if remaining_cap <= 0:
        result["cap_reached"] = True
        logger.info("Free-channel daily cap reached (%d/24h) - skipping publish",
                    settings.free_daily_cap)
        return result

    published_recent = [
        (row["id"], row["title_norm"])
        for row in db.recent_published_titles(hours=48)
    ]

    for row in db.select_to_publish(25, settings.max_article_age_hours):
        norm = row["title_norm"] or normalize_title(row["title"])

        # Already on the channel? exact / fuzzy title / same event.
        dup_of = find_duplicate(norm, published_recent, settings.dedupe_threshold)
        if not dup_of:
            for published_id, published_norm in published_recent:
                if same_event(norm, published_norm or ""):
                    dup_of = published_id
                    break
        if dup_of:
            db.mark_duplicate(row["id"], dup_of)
            result["duplicates"] += 1
            logger.info("Repeat suppressed: %s", row["title"][:80])
            continue

        try:
            text = format_post(row, settings)
            message_id = publisher.publish(settings.telegram_free_channel, text)
            db.mark_published(row["id"], settings.telegram_free_channel, message_id)
            result["published"] = 1
        except Exception as exc:  # noqa: BLE001 - the bot keeps running
            logger.error("Publish failed for article %s: %s", row["id"], exc)
        break

    return result


def run_cycle(settings: Settings | None = None, publisher=None, publish_limit: int = 1) -> dict:
    """One-off convenience: collect + up to `publish_limit` posts (scripts)."""
    settings = settings or get_settings()
    publisher = publisher or make_publisher(settings)

    stats = run_collect(settings)
    stats.update({"published": 0, "publish_duplicates": 0})

    for _ in range(max(1, publish_limit)):
        outcome = publish_next(settings, publisher)
        stats["published"] += outcome["published"]
        stats["publish_duplicates"] += outcome["duplicates"]
        if not outcome["published"]:
            break
        time.sleep(_PUBLISH_PAUSE_SECONDS)

    logger.info("Cycle done: %s", stats)
    return stats


def publish_premium_batch(settings: Settings | None = None, publisher=None) -> dict:
    """Premium channel: the complete feed, `premium_publish_batch` per tick.

    Premium carries every analyzed story - including the ones already sent to
    the free channel - and publishes faster, so members get early access.
    Same-event repeats within the premium channel are still suppressed.
    """
    settings = settings or get_settings()
    if not settings.telegram_premium_channel:
        return {"published": 0, "duplicates": 0, "configured": False}
    publisher = publisher or make_publisher(settings)
    db.init_db()

    result = {"published": 0, "duplicates": 0, "configured": True}
    premium_recent = [
        (row["id"], row["title_norm"])
        for row in db.recent_premium_titles(hours=48)
    ]

    for row in db.select_to_publish_premium(settings.premium_publish_batch,
                                            settings.max_article_age_hours):
        norm = row["title_norm"] or normalize_title(row["title"])
        dup_of = find_duplicate(norm, premium_recent, settings.dedupe_threshold)
        if not dup_of:
            for premium_id, premium_norm in premium_recent:
                if same_event(norm, premium_norm or ""):
                    dup_of = premium_id
                    break
        if dup_of:
            db.mark_duplicate(row["id"], dup_of)
            result["duplicates"] += 1
            continue

        try:
            text = format_post(row, settings, premium=True)
            message_id = publisher.publish(settings.telegram_premium_channel, text)
            db.mark_premium_published(row["id"], settings.telegram_premium_channel, message_id)
            premium_recent.append((row["id"], norm))
            result["published"] += 1
        except Exception as exc:  # noqa: BLE001 - keep the batch going
            logger.error("Premium publish failed for article %s: %s", row["id"], exc)
        time.sleep(0.3)

    if result["published"] or result["duplicates"]:
        logger.info("Premium batch: %s", result)
    return result
