"""Verify the bot token and show chats the bot has seen (to find a channel id).

Run: python scripts/check_bot.py   (token comes from .env - never printed)

- getMe       -> shows the bot's @username (you need it to add the bot as a
                 channel admin in the Telegram app).
- getUpdates  -> lists chats from recent updates. After you add the bot as a
                 channel admin and make any post in the channel, the channel
                 (with its -100... id) appears here - this is how we discover
                 the TELEGRAM_FREE_CHANNEL value for private channels.
"""
from __future__ import annotations

import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    from config import get_settings

    settings = get_settings()
    if not settings.has_telegram:
        print("TELEGRAM_BOT_TOKEN is not set in .env")
        return 1

    api = f"https://api.telegram.org/bot{settings.telegram_bot_token}"

    me = httpx.get(f"{api}/getMe", timeout=15).json()
    if not me.get("ok"):
        print("Token check FAILED:", me.get("description"))
        return 1
    bot = me["result"]
    print(f"Bot OK: {bot['first_name']} (@{bot['username']}) id={bot['id']}")
    print(f"  -> Add this bot as channel admin: @{bot['username']}")
    print()

    upd = httpx.get(f"{api}/getUpdates", timeout=15).json()
    if not upd.get("ok"):
        print("getUpdates failed:", upd.get("description"))
        return 1

    seen = False
    for update in upd.get("result", []):
        for key in ("channel_post", "edited_channel_post", "message", "my_chat_member"):
            payload = update.get(key)
            if not payload:
                continue
            chat = payload.get("chat", {})
            chat_id = chat.get("id")
            if chat_id is None:
                continue
            title = chat.get("title") or chat.get("first_name") or "?"
            username = f"@{chat['username']}" if chat.get("username") else ""
            print(f"update via {key}: chat id = {chat_id} | {title} {username}".strip())
            seen = True

    if not seen:
        print("No recent updates yet.")
        print("After you add the bot to the channel and post something there,")
        print("run this script again to see the channel id.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
