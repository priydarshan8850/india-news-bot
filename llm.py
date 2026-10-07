"""LLM analysis: DeepSeek via the OpenAI-compatible API, or an offline mock.

- Live mode needs DEEPSEEK_API_KEY (any OpenAI-compatible endpoint works,
  including a local Ollama server - see .env.example).
- Mock mode (LLM_MOCK=1, or no key configured) produces deterministic
  heuristic results so the whole pipeline can run and be tested offline.
"""
from __future__ import annotations

import json
import logging
import re
import time

from config import Settings, get_settings
from models import RawItem
from prompts import system_prompt, user_prompt

logger = logging.getLogger(__name__)

VALID_ORIENTATIONS = {"left", "right", "neutral", "mixed"}
VALID_IMPORTANCE = {"breaking", "high", "normal"}
VALID_RELIGION = {"hindu", "muslim", "christian", "sikh", "other"}


class LLMError(RuntimeError):
    """Raised when analysis failed after retries."""


# ---------------------------------------------------------------------------
# Response parsing / validation
# ---------------------------------------------------------------------------

def _extract_json(text: str) -> dict:
    """Parse the first JSON object found in a model reply."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise LLMError("no JSON object in model reply")
    return json.loads(match.group(0))


def _validate(raw: dict) -> dict:
    """Coerce the model's reply into our strict schema."""
    orientation = str(raw.get("political_orientation", "")).lower()
    importance = str(raw.get("importance", "")).lower()

    religion = raw.get("religion_topic")
    if religion is not None:
        religion = str(religion).lower()
        religion = religion if religion in VALID_RELIGION else None

    topics = raw.get("topics") or []
    if isinstance(topics, str):
        topics = [part.strip() for part in topics.split(",")]
    topics = [str(t).lower() for t in topics if str(t).strip()][:4]

    try:
        confidence = float(raw.get("confidence", 0.5))
    except (TypeError, ValueError):
        confidence = 0.5

    return {
        "political_orientation": orientation if orientation in VALID_ORIENTATIONS else "mixed",
        "topics": topics,
        "religion_topic": religion,
        "importance": importance if importance in VALID_IMPORTANCE else "normal",
        "summary": str(raw.get("summary", "")).strip(),
        "confidence": max(0.0, min(1.0, confidence)),
    }


# ---------------------------------------------------------------------------
# Offline mock (heuristic)
# ---------------------------------------------------------------------------

_BREAKING_WORDS = {
    "dies", "killed", "dead", "blast", "explosion", "earthquake", "flood",
    "cyclone", "war", "missile", "resigns", "emergency", "attacked", "crash",
    "collapse", "collapses", "collapsed", "trapped", "shooting", "shot",
}
_HIGH_WORDS = {
    "supreme court", "parliament", "election", "verdict", "arrested",
    "protest", "strike", "budget", "gst", "crisis", "ban",
}
_TOPIC_KEYWORDS = {
    "politics": ["election", "parliament", "minister", "party", "vote", "assembly", "bjp", "congress"],
    "economy": ["economy", "gdp", "inflation", "rupee", "market", "sensex", "bank", "budget", "gst", "trade"],
    "crime": ["arrested", "police", "murder", "fraud", "court", "cbi", "crime", "case"],
    "defence": ["army", "navy", "air force", "missile", "border", "defence", "defense", "security"],
    "international": ["china", "pakistan", "russia", "ukraine", "foreign", "global", "united nations"],
    "health": ["hospital", "health", "disease", "virus", "vaccine", "dengue", "covid", "outbreak"],
    "education": ["school", "college", "exam", "university", "students"],
    "technology": ["tech", "artificial intelligence", "isro", "satellite", "startup", "digital"],
    "sports": ["cricket", "ipl", "match", "olympic", "hockey", "football"],
    "entertainment": ["bollywood", "film", "movie", "actor", "actress", "box office"],
    "environment": ["climate", "pollution", "monsoon", "heatwave", "wildlife", "forest"],
}
_RELIGION_KEYWORDS = {
    "hindu": ["temple", "pooja", "puja", "hindu"],
    "muslim": ["mosque", "muslim", "islamic", "ramzan", "eid"],
    "christian": ["church", "christian", "christmas"],
    "sikh": ["gurdwara", "gurudwara", "sikh"],
}


def _has_word(text: str, words) -> bool:
    """Whole-word match - plain substring matching makes 'war' match 'warned'."""
    return any(re.search(rf"\b{re.escape(word)}\b", text) for word in words)


def _mock_analysis(item: RawItem) -> dict:
    text = f"{item.title} {item.summary}".lower()

    importance = "normal"
    if _has_word(text, _BREAKING_WORDS):
        importance = "breaking"
    elif _has_word(text, _HIGH_WORDS):
        importance = "high"

    topics = [
        topic for topic, words in _TOPIC_KEYWORDS.items()
        if _has_word(text, words)
    ][:3]

    religion = None
    for name, words in _RELIGION_KEYWORDS.items():
        if _has_word(text, words):
            religion = name
            break

    raw_text = item.content or item.summary or item.title
    sentences = re.split(r"(?<=[.!?])\s+", raw_text.strip())
    summary = " ".join(sentences[:2])[:400]

    return {
        "political_orientation": "neutral",
        "topics": topics,
        "religion_topic": religion,
        "importance": importance,
        "summary": summary,
        "confidence": 0.4,
    }


# ---------------------------------------------------------------------------
# DeepSeek / OpenAI-compatible live analysis
# ---------------------------------------------------------------------------

_client = None


def _openai_client(settings: Settings):
    global _client
    if _client is None:
        from openai import OpenAI
        _client = OpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            timeout=60,
        )
    return _client


def _live_analysis(item: RawItem, settings: Settings) -> dict:
    client = _openai_client(settings)
    messages = [
        {"role": "system", "content": system_prompt(settings.summary_language)},
        {"role": "user", "content": user_prompt(item.title, item.content or item.summary, item.source_name, item.url)},
    ]
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            resp = client.chat.completions.create(
                model=settings.deepseek_model,
                messages=messages,
                temperature=0.3,
                max_tokens=700,
                response_format={"type": "json_object"},
            )
            content = resp.choices[0].message.content or ""
            return _validate(_extract_json(content))
        except Exception as exc:  # noqa: BLE001 - surface any provider error after retries
            last_error = exc
            wait = 2 * (attempt + 1)
            logger.warning("LLM call failed (attempt %d/3): %s", attempt + 1, exc)
            if attempt < 2:
                time.sleep(wait)
    raise LLMError(f"DeepSeek analysis failed: {last_error}")


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def analyze(item: RawItem, settings: Settings | None = None) -> dict:
    """Classify + summarize one article. Returns the validated schema."""
    settings = settings or get_settings()
    if settings.use_mock_llm:
        return _validate(_mock_analysis(item))
    return _live_analysis(item, settings)
