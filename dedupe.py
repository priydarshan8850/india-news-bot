"""Duplicate detection: URL hashing + fuzzy title matching.

Exact URL matches are handled by the UNIQUE constraint in the database.
Fuzzy matching catches the same story re-published with a slightly different
title or tracked URL. Story-level clustering across outlets (embeddings) is a
later upgrade - see README "Phase 3".
"""
from __future__ import annotations

import hashlib
import re
from difflib import SequenceMatcher
from typing import Optional

_NORM_RE = re.compile(r"[^a-z0-9 ]+")


def url_hash(url: str) -> str:
    """Stable hash of the canonical URL (case/whitespace insensitive)."""
    return hashlib.sha1(url.strip().lower().encode("utf-8")).hexdigest()


def normalize_title(title: str) -> str:
    """Lowercase, strip punctuation - the comparable form of a headline."""
    text = title.lower().replace("&", " and ")
    text = _NORM_RE.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


def find_duplicate(
    title_norm: str,
    recent: list[tuple[int, Optional[str]]],
    threshold: float,
) -> Optional[int]:
    """Return the id of an already-seen article with a similar title, if any.

    `recent` is [(article_id, normalized_title), ...] from the last N hours.
    """
    if not title_norm:
        return None
    for article_id, other in recent:
        if not other:
            continue
        if title_norm == other:
            return article_id
        # Cheap length guard: unrelated-length titles can't be near-duplicates.
        if abs(len(title_norm) - len(other)) <= 40:
            ratio = SequenceMatcher(None, title_norm, other).ratio()
            if ratio >= threshold:
                return article_id
    return None


# ---------------------------------------------------------------------------
# Same-event detection ("the Seemapuri collapse posted by 3 outlets" problem)
# ---------------------------------------------------------------------------

# Words too common to prove two headlines are about the same event.
_STOPWORDS = {
    "about", "after", "again", "against", "ahead", "amid", "among",
    "another", "before", "being", "between", "breaking", "claim", "claims",
    "could", "during", "from", "have", "india", "indian", "indians",
    "latest", "live", "major", "more", "most", "news", "over", "report",
    "reports", "said", "says", "their", "there", "these", "they", "this",
    "those", "today", "tomorrow", "under", "update", "updates", "video",
    "watch", "what", "when", "where", "which", "while", "will", "with",
    "would", "yesterday",
}


def _significant_words(title_norm: str) -> set[str]:
    return {w for w in title_norm.split() if len(w) >= 5 and w not in _STOPWORDS}


def same_event(
    title_norm_a: str,
    title_norm_b: str,
    min_shared: int = 3,
    min_ratio: float = 0.35,
) -> bool:
    """True when two differently-worded headlines look like the same story.

    Compares significant words (5+ letters, stopwords removed): both headlines
    must share at least `min_shared` of them AND a decent share ratio. Example:
    "Few suspected trapped after portion of building collapses in Delhi's
    Seemapuri" ~= "Many Trapped As 5-Storey Building Collapses In Delhi...".
    """
    words_a = _significant_words(title_norm_a)
    words_b = _significant_words(title_norm_b)
    if not words_a or not words_b:
        return False
    shared = words_a & words_b
    if len(shared) < min_shared:
        return False
    return (len(shared) / min(len(words_a), len(words_b))) >= min_ratio
