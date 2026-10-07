"""Verify the LLM API key (DeepSeek by default) with a tiny test call.

Run: python scripts/check_llm.py
Reads the key from .env - it is never printed.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    from config import get_settings

    settings = get_settings()
    if settings.use_mock_llm:
        print("No DEEPSEEK_API_KEY set (or LLM_MOCK=1) -> mock mode, nothing to verify.")
        return 0

    print(f"Provider : {settings.deepseek_base_url}")
    print(f"Model    : {settings.deepseek_model}")

    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            timeout=30,
        )
        resp = client.chat.completions.create(
            model=settings.deepseek_model,
            messages=[{"role": "user", "content": "Reply with exactly: OK"}],
            max_tokens=5,
            temperature=0,
        )
        text = (resp.choices[0].message.content or "").strip()
        print(f"Response : {text!r}")
        print("LLM key OK - the bot will use real AI summaries.")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"LLM check FAILED: {exc}")
        print("Check the key and account balance at platform.deepseek.com,")
        print("or set LLM_MOCK=1 in .env to keep testing offline.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
