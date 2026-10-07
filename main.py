"""Entry point: `python main.py` (or double-click run.bat)."""
from __future__ import annotations

import logging
import sys


def _enable_truststore() -> None:
    """Verify TLS against the OS certificate store.

    Same fix as used in AIRREV: on corporate networks an HTTPS-inspecting
    proxy signs traffic with a private root CA that certifi doesn't know,
    which produces CERTIFICATE_VERIFY_FAILED on every outbound API call.
    """
    try:
        import truststore
        truststore.inject_into_ssl()
    except ImportError:
        pass


HOW_TO_GET_TOKEN = """\
TELEGRAM_BOT_TOKEN is not set. To create one (2 minutes):
  1. Open Telegram and message @BotFather
  2. Send /newbot, choose a name and a username
  3. Copy the token into .env next to TELEGRAM_BOT_TOKEN=
     (it looks like 123456789:AA...)
  4. Create a channel, add the bot as administrator with "Post messages",
     and put the channel @name into TELEGRAM_FREE_CHANNEL=
Then run: python main.py"""


def main() -> int:
    _enable_truststore()

    from config import get_settings
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    # HTTP clients log full request URLs - which include the bot token. Keep
    # them quiet so cloud log viewers never see the token.
    for noisy in ("httpx", "httpx2", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    import db
    db.init_db()

    if not settings.telegram_bot_token:
        print(HOW_TO_GET_TOKEN)
        return 1
    if not settings.telegram_free_channel:
        print(
            "TELEGRAM_FREE_CHANNEL is not set.\n"
            "Create a channel, add the bot as admin (Post messages permission), "
            "and set e.g. TELEGRAM_FREE_CHANNEL=@my_india_news in .env"
        )
        return 1

    if settings.use_mock_llm:
        print("WARNING: LLM mock mode is ON - summaries are offline heuristics, not AI output.")
        print("Set DEEPSEEK_API_KEY in .env for real analysis, or keep mock for testing.")

    from bot import build_application

    application = build_application(settings)
    print("Bot is running (long polling). Press Ctrl+C to stop.")
    print(f"Collect every {settings.collect_interval_minutes} min | "
          f"post every {settings.publish_interval_minutes} min | "
          f"daily cap {settings.free_daily_cap} | "
          f"LLM: {settings.deepseek_model if not settings.use_mock_llm else 'mock'}")
    application.run_polling(drop_pending_updates=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
