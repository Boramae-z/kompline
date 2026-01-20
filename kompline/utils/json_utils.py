"""JSON parsing helpers for LLM outputs."""

from __future__ import annotations

import json
import re
from typing import Any


def extract_json(value: Any) -> Any | None:
    """Best-effort JSON extraction from LLM output."""
    if isinstance(value, (dict, list)):
        return value
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    # Direct parse
    parsed = _try_parse(text)
    if parsed is not None:
        return parsed

    # Fenced blocks
    for pattern in (r"```json(.*?)```", r"```(.*?)```"):
        match = re.search(pattern, text, re.S | re.I)
        if match:
            candidate = match.group(1).strip()
            parsed = _try_parse(candidate)
            if parsed is not None:
                return parsed

    # Fallback: try parsing substrings that look like JSON
    first_brace = _first_json_start(text)
    if first_brace is None:
        return None

    for end in range(len(text), first_brace, -1):
        candidate = text[first_brace:end].strip()
        parsed = _try_parse(candidate)
        if parsed is not None:
            return parsed

    return None


def _try_parse(text: str) -> Any | None:
    try:
        return json.loads(text)
    except Exception:
        return None


def _first_json_start(text: str) -> int | None:
    for i, ch in enumerate(text):
        if ch in "{[":
            return i
    return None
