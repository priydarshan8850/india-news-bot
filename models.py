"""Shared data structures used across collectors, database and pipeline."""
from __future__ import annotations

import html
import re
from dataclasses import dataclass
from typing import Optional

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def clean_html(text: Optional[str]) -> str:
    """Strip HTML tags/entities and collapse whitespace."""
    if not text:
        return ""
    text = html.unescape(text)
    text = _TAG_RE.sub(" ", text)
    return _WS_RE.sub(" ", text).strip()


@dataclass
class RawItem:
    """One collected news item, before any analysis."""

    url: str
    title: str
    summary: str = ""
    content: str = ""
    source_name: str = ""
    source_type: str = "rss"            # "rss" | "telegram" | "x"
    published_at: Optional[str] = None  # "YYYY-MM-DD HH:MM:SS" UTC


@dataclass
class Analysis:
    """The LLM's structured verdict about one item."""

    political_orientation: str = "mixed"    # neutral | left | right | mixed
    topics: list = None                     # type: ignore[assignment]
    religion_topic: Optional[str] = None    # hindu | muslim | christian | sikh | other | None
    importance: str = "normal"              # breaking | high | normal
    summary: str = ""
    confidence: float = 0.5

    def __post_init__(self) -> None:
        if self.topics is None:
            self.topics = []
