"""Tweet the next TOP story when it is due - the affordable "X Mode".

Why text-only: X charges $0.20 per post containing a URL but $0.015 for plain
text. Tweets therefore carry the headline + summary + hashtags + a Telegram
pointer (no link), which also funnels X readers to the channel.

Pacing: at most one tweet per X_MIN_GAP_MINUTES (default 60), and never more
than X_DAILY_LIMIT (default 15) per UTC day. Runs inside the GitHub workflow;
no-ops gracefully until the X_* repository secrets are added.

State file: queue/x_state.json
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import html
import json
import os
import re
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUEUE_FILE = ROOT / "queue" / "posts.json"
STATE_FILE = ROOT / "queue" / "x_state.json"
TWEET_URL = "https://api.x.com/2/tweets"
TWEET_LIMIT = 280
DEFAULT_FOOTER = "📲 Full feed on Telegram: @indian_news_nationalist"


def _strip_html(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html.unescape(text or ""))).strip()


def build_tweet(entry: dict, footer: str) -> str:
    """Compose a <=280-char tweet from a queue entry."""
    title = _strip_html(entry.get("title", ""))
    full_text = entry.get("text", "")
    match = re.search(r"📝 (.*?)\n\n🔗", full_text, re.DOTALL)
    summary = _strip_html(match.group(1)) if match else ""
    hashtags = next(
        (line.strip() for line in full_text.splitlines() if line.strip().startswith("#IndiaNews")),
        "#IndiaNews",
    )

    def compose(t: str, s: str) -> str:
        body = f"🇮🇳 {t}"
        if s:
            body += f"\n\n{s}"
        return f"{body}\n\n{hashtags}\n{footer}"

    tweet = compose(title, summary)
    if len(tweet) > TWEET_LIMIT and summary:
        short = summary
        while short and len(compose(title, short)) > TWEET_LIMIT:
            short = short[:-12].rstrip()
        if short and short != summary:
            short += "…"
        tweet = compose(title, short)
    if len(tweet) > TWEET_LIMIT:
        short_title = title
        while short_title and len(compose(short_title, "")) > TWEET_LIMIT:
            short_title = short_title[:-12].rstrip()
        tweet = compose(short_title + "…", "")
    return tweet[:TWEET_LIMIT]


def oauth1_header(method: str, url: str, consumer_key: str, consumer_secret: str,
                  token: str, token_secret: str) -> str:
    params = {
        "oauth_consumer_key": consumer_key,
        "oauth_nonce": secrets.token_hex(16),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": token,
        "oauth_version": "1.0",
    }
    enc = lambda value: urllib.parse.quote(str(value), safe="")
    param_string = "&".join(f"{enc(k)}={enc(v)}" for k, v in sorted(params.items()))
    base = f"{method.upper()}&{enc(url)}&{enc(param_string)}"
    signing_key = f"{enc(consumer_secret)}&{enc(token_secret)}"
    digest = hmac.new(signing_key.encode(), base.encode(), hashlib.sha1).digest()
    params["oauth_signature"] = base64.b64encode(digest).decode()
    return "OAuth " + ", ".join(f'{enc(k)}="{enc(v)}"' for k, v in params.items())


def post_tweet(text: str, key: str, secret: str, token: str, token_secret: str) -> tuple[bool, str]:
    payload = json.dumps({"text": text}).encode("utf-8")
    request = urllib.request.Request(
        TWEET_URL,
        data=payload,
        method="POST",
        headers={
            "Authorization": oauth1_header("POST", TWEET_URL, key, secret, token, token_secret),
            "Content-Type": "application/json",
            "User-Agent": "india-news-bot/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = json.loads(response.read().decode("utf-8"))
            return True, str(body.get("data", {}).get("id", "ok"))
    except urllib.error.HTTPError as exc:
        return False, f"HTTP {exc.code}: {exc.read().decode(errors='replace')[:300]}"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)[:200]


def _save(state: dict) -> None:
    STATE_FILE.parent.mkdir(exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=1), encoding="utf-8")


def main() -> int:
    key = os.environ.get("X_API_KEY", "").strip()
    secret = os.environ.get("X_API_SECRET", "").strip()
    token = os.environ.get("X_ACCESS_TOKEN", "").strip()
    token_secret = os.environ.get("X_ACCESS_SECRET", "").strip()
    footer = os.environ.get("X_FOOTER", DEFAULT_FOOTER).strip() or DEFAULT_FOOTER

    if not all([key, secret, token, token_secret]):
        print("X keys not configured - skipping X Mode (add the X_* repo secrets to enable).")
        return 0

    entries = json.loads(QUEUE_FILE.read_text(encoding="utf-8")) if QUEUE_FILE.exists() else []
    state = json.loads(STATE_FILE.read_text(encoding="utf-8")) if STATE_FILE.exists() else {}
    state.setdefault("next", 0)
    state.setdefault("count_today", 0)
    state.setdefault("day", "")
    state.setdefault("last_sent_epoch", 0)

    today = time.strftime("%Y-%m-%d", time.gmtime())
    if state["day"] != today:
        state["day"] = today
        state["count_today"] = 0

    limit = int(os.environ.get("X_DAILY_LIMIT", "15"))
    min_gap = int(os.environ.get("X_MIN_GAP_MINUTES", "60")) * 60
    index = int(state["next"])

    if index >= len(entries):
        _save(state)
        print(f"X queue empty ({index}/{len(entries)}).")
        return 0
    if state["count_today"] >= limit:
        _save(state)
        print(f"X daily limit reached ({state['count_today']}/{limit}).")
        return 0
    last = int(state.get("last_sent_epoch", 0) or 0)
    now = time.time()
    if last and now - last < min_gap:
        _save(state)
        print(f"X not due yet - {int((min_gap - (now - last)) // 60)} min to go.")
        return 0

    entry = entries[index]
    tweet = build_tweet(entry, footer)
    ok, message = post_tweet(tweet, key, secret, token, token_secret)
    print(f"{'Tweeted' if ok else 'Tweet failed'} #{index}: {entry.get('title', '')[:60]} | {message}")

    if ok:
        state["next"] = index + 1
        state["count_today"] += 1
        state["last_sent_epoch"] = int(now)
        state["last_tweet_at"] = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
        state["fail_count"] = 0
    else:
        # Retry the same item a couple of times, then skip it so the queue
        # never gets stuck on a tweet X refuses (e.g. duplicate content).
        if state.get("fail_index") == index:
            state["fail_count"] = int(state.get("fail_count", 0)) + 1
        else:
            state["fail_index"] = index
            state["fail_count"] = 1
        if state["fail_count"] >= 3:
            print(f"Skipping item #{index} after 3 failures.")
            state["next"] = index + 1
            state["fail_count"] = 0
    _save(state)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
