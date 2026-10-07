"""Create the ₹25/month Telegram Stars subscription link for the premium channel.

Prereqs (see SETUP_GUIDE Part G / README Phase 2):
  1. Create a PRIVATE channel (e.g. "India News — Premium").
  2. Add your bot as admin with: Post messages + Pin messages + Invite users via link.
  3. Put its id in .env:  TELEGRAM_PREMIUM_CHANNEL=-100...   (or @username if public)

Run:  python scripts/setup_premium.py      (or double-click premium_setup.bat)

The monthly subscription link is created via createChatInviteLink
(subscription_period = 30 days, subscription_price = PREMIUM_PRICE_STARS)
and saved to .env as PREMIUM_INVITE_LINK, which powers /premium and /subscribe.
Telegram handles the monthly billing and renewals; members cancel in the app.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    from config import get_settings

    settings = get_settings()
    if not settings.has_telegram:
        print("TELEGRAM_BOT_TOKEN is not set in .env.")
        return 1
    if not settings.telegram_premium_channel:
        print("TELEGRAM_PREMIUM_CHANNEL is not set in .env.\n"
              "1. Create a private channel\n"
              "2. Add the bot as admin (Post messages + Pin messages + Invite users via link)\n"
              "3. Set TELEGRAM_PREMIUM_CHANNEL=-100... (or @username) and re-run.")
        return 1

    api = f"https://api.telegram.org/bot{settings.telegram_bot_token}"

    chat = httpx.get(f"{api}/getChat",
                     params={"chat_id": settings.telegram_premium_channel},
                     timeout=20).json()
    if not chat.get("ok"):
        print("Chat check failed:", chat.get("description"))
        print("Hint: is the bot an admin of that channel and is the id correct?")
        return 1
    print("Channel OK:", chat["result"].get("title"))

    resp = httpx.post(
        f"{api}/createChatInviteLink",
        json={
            "chat_id": settings.telegram_premium_channel,
            "name": f"Premium monthly ({settings.premium_price_stars} stars)",
            "subscription_period": 2592000,  # 30 days - the only value Telegram accepts
            "subscription_price": settings.premium_price_stars,
        },
        timeout=30,
    ).json()

    if not resp.get("ok"):
        print("createChatInviteLink failed:", resp.get("description"))
        print("Hints:")
        print("  - the bot needs the admin right 'Invite users via link' (can_invite_users)")
        print("  - some channels need paid subscriptions/Stars enabled first - check the")
        print("    channel settings and https://core.telegram.org/bots/payments-stars")
        return 1

    link = resp["result"]["invite_link"]
    print("Monthly subscription link created:")
    print(" ", link)

    env_path = ROOT / ".env"
    text = env_path.read_text(encoding="utf-8")
    if re.search(r"^PREMIUM_INVITE_LINK=.*$", text, flags=re.MULTILINE):
        text = re.sub(r"^PREMIUM_INVITE_LINK=.*$", f"PREMIUM_INVITE_LINK={link}",
                      text, flags=re.MULTILINE)
    else:
        text = text.rstrip() + f"\nPREMIUM_INVITE_LINK={link}\n"
    env_path.write_text(text, encoding="utf-8")

    print(f"Saved to .env as PREMIUM_INVITE_LINK ({settings.premium_price_stars} stars ~= ₹25/month).")
    print("Restart the bot, then /premium and /subscribe hand out this join link.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
