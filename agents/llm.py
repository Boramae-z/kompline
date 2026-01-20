from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List, Optional

import requests

from agents.config import GPT_MODEL, OPENAI_API_KEY, OPENAI_BASE_URL

logger = logging.getLogger("agents.llm")


def _extract_response_text(payload: Dict[str, Any]) -> str:
    if payload.get("output_text"):
        return payload["output_text"]
    texts: List[str] = []
    for item in payload.get("output", []):
        if item.get("type") != "message":
            continue
        for part in item.get("content", []):
            if part.get("type") == "output_text" and part.get("text"):
                texts.append(part["text"])
    return "\n".join(texts).strip()


def call_openai_json(instructions: str, input_text: str, schema: Dict[str, Any]) -> Dict[str, Any]:
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not set")

    payload = {
        "model": GPT_MODEL,
        "instructions": instructions,
        "input": input_text,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "agent_response",
                "schema": schema,
                "strict": True,
            }
        },
        "temperature": 0,
    }

    last_error: Optional[str] = None
    for attempt in range(3):
        logger.debug("OpenAI request attempt=%s model=%s input_chars=%s", attempt + 1, GPT_MODEL, len(input_text))
        response = requests.post(
            f"{OPENAI_BASE_URL}/responses",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=180,
        )

        logger.debug("OpenAI response status=%s body=%s", response.status_code, response.text[:4000])

        if response.status_code == 200:
            payload_json = response.json()
            text = _extract_response_text(payload_json)
            try:
                return json.loads(text)
            except json.JSONDecodeError as exc:
                last_error = f"Invalid JSON from model: {exc}"
                break

        last_error = f"OpenAI responses error: {response.status_code} {response.text}"
        if response.status_code in {429, 500, 502, 503, 504} and attempt < 2:
            time.sleep(2 * (attempt + 1))
            continue
        break

    raise RuntimeError(last_error or "OpenAI responses error")
