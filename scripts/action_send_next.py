"""Send ONE queued post to Telegram - executed by the GitHub Actions robot.

Reads queue/posts.json + queue/state.json, sends posts[next], then writes the
advanced cursor back. The GitHub runner calls this every 5 minutes, so posts
keep flowing while your PC is off. Standard library only - no dependencies.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
QUEUE_FILE = ROOT / "queue" / "posts.json"
STATE_FILE = ROOT / "queue" / "state.json"


def _post(url: str, payload: dict) -> tuple[int, dict]:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            return exc.code, json.loads(body)
        except json.JSONDecodeError:
            return exc.code, {"description": body[:200]}


def _add_buttons(api: str, channel: str, message_id: int) -> None:
    """Share / Invite buttons - same as the PC bot adds. Best effort."""
    if not channel.startswith("@"):
        return
    handle = channel.lstrip("@")
    post_url = f"https://t.me/{handle}/{message_id}"
    share_url = (
        "https://t.me/share/url?url=" + quote(post_url, safe="")
        + "&text=" + quote(f"via @{handle}", safe="")
    )
    invite_url = (
        "https://t.me/share/url?url=" + quote(f"https://t.me/{handle}", safe="")
        + "&text=" + quote("🇮🇳 24x7 India news — AI summaries, always linked.", safe="")
    )
    try:
        _post(f"{api}/editMessageReplyMarkup", {
            "chat_id": channel,
            "message_id": message_id,
            "reply_markup": {"inline_keyboard": [[
                {"text": "📤 Share", "url": share_url},
                {"text": "➕ Invite friends", "url": invite_url},
            ]]},
        })
    except Exception as exc:  # noqa: BLE001 - buttons are a bonus
        print(f"(buttons skipped: {exc})")


def main() -> int:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    channel = os.environ.get("TELEGRAM_FREE_CHANNEL", "").strip()
    if not token or not channel:
        print("Missing TELEGRAM_BOT_TOKEN / TELEGRAM_FREE_CHANNEL repository secrets.")
        return 1

    if not QUEUE_FILE.exists():
        print("No queue file yet - run push_queue.bat on the PC first.")
        return 0

    posts = json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
    state = json.loads(STATE_FILE.read_text(encoding="utf-8")) if STATE_FILE.exists() else {"next": 0}
    index = int(state.get("next", 0))

    if index >= len(posts):
        print(f"Queue empty ({index}/{len(posts)}) - top up with push_queue.bat on the PC.")
        return 0

    item = posts[index]
    api = f"https://api.telegram.org/bot{token}"
    sent_ok = False
    for attempt in range(3):
        status, result = _post(f"{api}/sendMessage", {
            "chat_id": channel, "text": item["text"], "parse_mode": "HTML",
        })
        if result.get("ok"):
            sent_ok = True
            print(f"Sent #{index}: {item['title'][:70]}")
            _add_buttons(api, channel, int(result["result"]["message_id"]))
            break
        print(f"Attempt {attempt + 1} failed ({status}): {result.get('description')}")
        if status == 429:
            time.sleep(10 * (attempt + 1))
        else:
            time.sleep(4)

    # Advance the cursor even on failure - one bad post must not block the queue.
    state["next"] = index + 1
    state["last_attempt_at"] = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
    state["last_result"] = "ok" if sent_ok else "failed"
    STATE_FILE.write_text(json.dumps(state, indent=1), encoding="utf-8")
    print(f"Cursor -> {state['next']}/{len(posts)}")
    return 0 if sent_ok else 1


if __name__ == "__main__":
    sys.exit(main())
