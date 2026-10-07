"""Post + pin a channel intro so the channel looks professional.

Run:  python scripts/send_intro.py     (or double-click send_intro.bat)
"""
from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import quote

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

INTRO = """🇮🇳 <b>Welcome to India News</b>

Your daily pulse of India — in one channel.

✅ Aggregated from 25+ trusted sources (websites, YouTube, Telegram)
🧠 Every story is de-duplicated and AI-summarised in 2–4 neutral sentences
🏷 Labelled: Neutral / Left / Right framing • Breaking / High / Normal importance
🔗 Every post links to the original source

🕐 Updated 24×7, automatically.

<i>Summaries are AI-generated for information only — always check the linked source.</i>"""


def main() -> int:
    from config import get_settings
    settings = get_settings()

    if not settings.has_telegram or not settings.telegram_free_channel:
        print("Set TELEGRAM_BOT_TOKEN and TELEGRAM_FREE_CHANNEL in .env first.")
        return 1

    api = f"https://api.telegram.org/bot{settings.telegram_bot_token}"

    # Only the fresh intro should stay pinned.
    httpx.post(
        f"{api}/unpinAllChatMessages",
        json={"chat_id": settings.telegram_free_channel},
        timeout=30,
    )

    text = INTRO
    if settings.telegram_free_channel.startswith("@"):
        handle = settings.telegram_free_channel.lstrip("@")
        invite_url = (
            "https://t.me/share/url?url=" + quote(f"https://t.me/{handle}", safe="")
            + "&text=" + quote("🇮🇳 24x7 India news — AI summaries, always linked.", safe="")
        )
        text += f'\n\n📤 <b>Help us grow:</b> <a href="{invite_url}">invite your friends</a>'

    sent = httpx.post(
        f"{api}/sendMessage",
        json={"chat_id": settings.telegram_free_channel, "text": text, "parse_mode": "HTML"},
        timeout=30,
    ).json()
    if not sent.get("ok"):
        print(f"Failed to post intro: {sent.get('description')}")
        print("Hint: is the bot an administrator of the channel, with 'Post messages' allowed?")
        return 1
    message_id = sent["result"]["message_id"]
    print(f"Intro posted (message id {message_id}).")

    pinned = httpx.post(
        f"{api}/pinChatMessage",
        json={
            "chat_id": settings.telegram_free_channel,
            "message_id": message_id,
            "disable_notification": True,
        },
        timeout=30,
    ).json()
    if pinned.get("ok"):
        print("Intro pinned. The channel now has a proper welcome post.")
    else:
        print(f"Posted, but pinning failed: {pinned.get('description')}")
        print("(The bot needs the 'Pin messages' admin right in the channel.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
