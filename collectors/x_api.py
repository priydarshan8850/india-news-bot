"""Optional X (Twitter) collector using the v2 recent-search API.

IMPORTANT: X's API is paid - the free tier cannot read others' posts. Without
a paid bearer token this collector is simply skipped.

Requires: X_BEARER_TOKEN in .env and account handles in feeds.yaml -> x_accounts.
"""
from __future__ import annotations

import logging

import httpx

from models import RawItem, clean_html

logger = logging.getLogger(__name__)

SEARCH_URL = "https://api.x.com/2/tweets/search/recent"


def collect_x(accounts: list[str], bearer_token: str, max_per_account: int = 5) -> list[RawItem]:
    handles = [str(a).strip().lstrip("@") for a in accounts or [] if str(a).strip()]
    if not handles or not bearer_token:
        return []

    query = "(" + " OR ".join(f"from:{handle}" for handle in handles) + ") -is:retweet -is:reply"
    max_results = max(10, min(100, max_per_account * len(handles)))
    try:
        resp = httpx.get(
            SEARCH_URL,
            params={"query": query, "max_results": max_results, "tweet.fields": "created_at"},
            headers={"Authorization": f"Bearer {bearer_token}"},
            timeout=30,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("X API request failed: %s", exc)
        return []

    if resp.status_code != 200:
        logger.warning(
            "X API returned %s (most plans need a paid tier): %s",
            resp.status_code, resp.text[:200],
        )
        return []

    items: list[RawItem] = []
    for tweet in resp.json().get("data", []):
        text = clean_html(tweet.get("text", ""))
        if not text:
            continue
        tweet_id = tweet.get("id")
        published_at = None
        if tweet.get("created_at"):
            published_at = tweet["created_at"].replace("T", " ").replace("Z", "")[:19]
        items.append(RawItem(
            url=f"https://x.com/i/web/status/{tweet_id}",
            title=text[:140],
            summary=text[:600],
            content=text[:6000],
            source_name="X",
            source_type="x",
            published_at=published_at,
        ))
    return items
