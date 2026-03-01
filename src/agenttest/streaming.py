from __future__ import annotations

import json


def parse_sse(raw: str) -> str:
    """Concatenate data: lines from Server-Sent Events stream, skipping [DONE]."""
    parts: list[str] = []
    for line in raw.splitlines():
        if line.startswith("data:"):
            # SSE spec: strip at most one leading space after "data:"
            payload = line[len("data:"):]
            if payload.startswith(" "):
                payload = payload[1:]
            if payload == "[DONE]":
                continue
            parts.append(payload)
    return "".join(parts)


def parse_ndjson(raw: str) -> str:
    """Parse newline-delimited JSON, extracting text content from common fields."""
    parts: list[str] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        # Try common content field patterns
        if isinstance(obj, dict):
            if "delta" in obj and isinstance(obj["delta"], dict):
                content = obj["delta"].get("content", "")
                if content:
                    parts.append(content)
                    continue
            for key in ("text", "content"):
                if key in obj and isinstance(obj[key], str):
                    parts.append(obj[key])
                    break
    return "".join(parts)


def parse_ai_sdk_ui(raw: str) -> str:
    """Parse Vercel AI SDK UI stream format: lines like 0:"text chunk"."""
    parts: list[str] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        # Format: 0:"chunk of text"
        if line.startswith('0:"') and line.endswith('"'):
            text = line[3:-1]
            # Unescape basic sequences
            text = text.replace('\\"', '"').replace("\\n", "\n").replace("\\\\", "\\")
            parts.append(text)
    return "".join(parts)


PARSERS: dict[str, callable] = {
    "sse": parse_sse,
    "ndjson": parse_ndjson,
    "ai-sdk-ui": parse_ai_sdk_ui,
}

VALID_MODES = frozenset(PARSERS.keys())
