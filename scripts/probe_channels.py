"""Probe public Telegram channels: shows the latest posts of each handle.

Use this to pick good entries for `telegram_channels` in feeds.yaml - some
handles that look official belong to squatters or reposters.

Run:  python scripts/probe_channels.py handle1 handle2 ...
Default handles used when none are given.
"""
from __future__ import annotations

import sys

import httpx
from bs4 import BeautifulSoup

DEFAULT_HANDLES = [
    "ndtv", "timesofindia", "indianexpress", "thehindu",
    "hindustantimes", "wionews", "firstpost", "livemint", "aajtak",
]


def probe(handle: str) -> None:
    name = handle.strip().lstrip("@")
    try:
        resp = httpx.get(
            f"https://t.me/s/{name}",
            timeout=20,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; IndiaNewsBot/1.0)"},
        )
    except Exception as exc:  # noqa: BLE001
        print(f"@{name:<16} -> error: {exc}")
        return

    soup = BeautifulSoup(resp.text, "html.parser")
    messages = soup.select("div.tgme_widget_message_text")
    if not messages:
        print(f"@{name:<16} -> HTTP {resp.status_code}: no public posts / preview disabled")
        return

    print(f"@{name:<16} -> HTTP {resp.status_code}:")
    for message in messages[-2:]:
        snippet = " ".join(message.get_text(" ").split())[:110]
        print(f"    • {snippet}")
    print()


if __name__ == "__main__":
    handles = sys.argv[1:] or DEFAULT_HANDLES
    for handle in handles:
        probe(handle)
