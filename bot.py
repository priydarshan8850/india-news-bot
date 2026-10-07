"""Telegram bot: command handlers + the scheduled pipeline cycle.

Runs in long-polling mode, so no public URL/webhook is needed - everything
works from a home PC behind a router.
"""
from __future__ import annotations

import asyncio
import html
import logging
from datetime import time as clock_time, timezone
from urllib.parse import quote

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    Defaults,
)

import db
from config import Settings
from digest import send_digest
from pipeline import publish_next, publish_premium_batch, run_collect

logger = logging.getLogger(__name__)

WELCOME = (
    "🇮🇳 <b>India News Bot</b>\n\n"
    "I collect India news from multiple sources, remove duplicates, classify "
    "each story and publish a neutral 2–4 sentence summary to the channel.\n\n"
    "Commands:\n"
    "/latest — last published stories\n"
    "/premium — ⭐ Premium (₹25/month)\n"
    "/subscribe — join the premium channel\n"
    "/help — this message"
)


def _settings(context: ContextTypes.DEFAULT_TYPE) -> Settings:
    return context.application.bot_data["settings"]


def _is_admin(update: Update, settings: Settings) -> bool:
    user = update.effective_user
    return bool(settings.admin_user_id and user and user.id == settings.admin_user_id)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    settings = _settings(context)
    text = WELCOME
    if settings.telegram_free_channel:
        if settings.telegram_free_channel.startswith("@"):
            handle = settings.telegram_free_channel.lstrip("@")
            invite_url = (
                "https://t.me/share/url?url=" + quote(f"https://t.me/{handle}", safe="")
                + "&text=" + quote("🇮🇳 24x7 India news — AI summaries, always linked.", safe="")
            )
            text += f'\n\n📢 {settings.telegram_free_channel}\n➕ Invite friends: <a href="{invite_url}">share link</a>'
        else:
            text += f"\n\n📢 {settings.telegram_free_channel}"
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)


async def cmd_latest(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    rows = await asyncio.to_thread(db.latest_published, 8)
    if not rows:
        await update.message.reply_text("No stories published yet — try again in a few minutes.")
        return
    lines = ["<b>Latest stories</b>"]
    for row in rows:
        title = html.escape(row["title"], quote=False)
        url = html.escape(row["url"] or "", quote=True)
        lines.append(f'• <a href="{url}">{title}</a>')
    await update.message.reply_text(
        "\n".join(lines), parse_mode=ParseMode.HTML, disable_web_page_preview=True
    )


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    settings = _settings(context)
    if not _is_admin(update, settings):
        await update.message.reply_text("This command is admin-only.")
        return
    data = await asyncio.to_thread(db.stats)
    lines = ["<b>News bot stats</b>"]
    lines += [f"{key}: <b>{value}</b>" for key, value in data.items()]
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


async def cmd_collect(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    settings = _settings(context)
    if not _is_admin(update, settings):
        await update.message.reply_text("This command is admin-only.")
        return
    await update.message.reply_text("Running a collection cycle…")
    collect_stats = await asyncio.to_thread(run_collect, settings)
    publish_result = await asyncio.to_thread(publish_next, settings, None)
    summary = ", ".join(f"{key}={value}" for key, value in collect_stats.items())
    await update.message.reply_text(f"Collect: {summary}\nPublish: {publish_result}")


async def cmd_premium(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    settings = _settings(context)
    stars = settings.premium_price_stars
    lines = [
        "⭐ <b>Premium — exclusive India news</b>",
        "",
        f"💰 <b>₹25/month</b> (~{stars} Telegram Stars, auto-renewing, cancel anytime)",
        "",
        "What you get:",
        "• <b>Full feed</b> — every story, not just the free highlights",
        "• <b>Early access</b> — premium members see stories first",
        "• <b>Morning + evening digests</b> — the day in one post",
        "• Every post neutral, sourced and duplicate-free",
        "",
    ]
    if settings.telegram_premium_channel and settings.premium_invite_link:
        lines.append(f'👉 <a href="{settings.premium_invite_link}">Join Premium</a>')
    elif settings.telegram_premium_channel:
        lines.append("Premium is being set up — the join link will appear here shortly.")
    else:
        lines.append("Premium channel launching soon. Follow the free channel meanwhile!")
    await update.message.reply_text(
        "\n".join(lines), parse_mode=ParseMode.HTML, disable_web_page_preview=True
    )


async def _collect_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = _settings(context)
    try:
        stats = await asyncio.to_thread(run_collect, settings)
        logger.info("Scheduled collect: %s", stats)
    except Exception:  # noqa: BLE001 - a failed job must not kill the bot
        logger.exception("Scheduled collect failed")


async def _publish_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = _settings(context)
    try:
        result = await asyncio.to_thread(publish_next, settings, None)
        if result["published"]:
            logger.info("Paced publish: one story posted")
    except Exception:  # noqa: BLE001
        logger.exception("Scheduled publish failed")


async def _premium_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = _settings(context)
    try:
        result = await asyncio.to_thread(publish_premium_batch, settings, None)
        if result.get("published"):
            logger.info("Premium batch: %s", result)
    except Exception:  # noqa: BLE001
        logger.exception("Premium publish failed")


async def _digest_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = _settings(context)
    try:
        sent = await asyncio.to_thread(send_digest, settings, None)
        if sent:
            logger.info("Premium digest sent")
    except Exception:  # noqa: BLE001
        logger.exception("Digest failed")


def build_application(settings: Settings) -> Application:
    app = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .defaults(Defaults(parse_mode=ParseMode.HTML))
        .build()
    )
    app.bot_data["settings"] = settings

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_start))
    app.add_handler(CommandHandler("latest", cmd_latest))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("collect", cmd_collect))
    app.add_handler(CommandHandler("premium", cmd_premium))
    app.add_handler(CommandHandler("subscribe", cmd_premium))

    if app.job_queue is None:
        raise RuntimeError(
            "JobQueue unavailable. Install the extra: pip install 'python-telegram-bot[job-queue]'"
        )
    collect_seconds = max(5, settings.collect_interval_minutes) * 60
    publish_seconds = max(1, settings.publish_interval_minutes) * 60
    app.job_queue.run_repeating(_collect_job, interval=collect_seconds, first=15, name="collect")
    app.job_queue.run_repeating(_publish_job, interval=publish_seconds, first=90, name="publish")

    if settings.telegram_premium_channel:
        premium_seconds = max(1, settings.premium_publish_interval_minutes) * 60
        app.job_queue.run_repeating(_premium_job, interval=premium_seconds, first=120,
                                    name="premium_publish")
        # 08:00 and 20:00 IST == 02:30 and 14:30 UTC
        app.job_queue.run_daily(_digest_job, time=clock_time(2, 30, tzinfo=timezone.utc),
                                name="digest_morning")
        app.job_queue.run_daily(_digest_job, time=clock_time(14, 30, tzinfo=timezone.utc),
                                name="digest_evening")

    return app
