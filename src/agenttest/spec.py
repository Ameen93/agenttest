from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class TurnSpec:
    user: str
    assertions: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class CaseSpec:
    id: str
    name: str
    input: dict[str, Any] | None = None
    assertions: list[dict[str, Any]] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    timeout: float | None = None
    flaky_threshold: str | None = None
    type: str = "single"
    turns: list[TurnSpec] = field(default_factory=list)


def parse_flaky_threshold(value: str) -> tuple[int, int]:
    """Parse 'N/M' format into (required_passes, total_attempts)."""
    parts = value.split("/")
    if len(parts) != 2:
        raise ValueError(f"flaky_threshold must be 'N/M' format, got '{value}'")
    required, total = int(parts[0]), int(parts[1])
    if required < 1 or total < 1 or required > total:
        raise ValueError(f"flaky_threshold {value}: need 1 <= N <= M")
    return required, total


@dataclass
class AdapterConfig:
    type: str = "http"
    url: str = ""
    method: str = "POST"
    headers: dict[str, str] = field(default_factory=dict)
    timeout: float = 30.0
    stream_mode: str | None = None


@dataclass
class Suite:
    name: str
    adapter: AdapterConfig
    tests: list[CaseSpec]


def _require(obj: dict[str, Any], key: str, context: str) -> Any:
    if key not in obj:
        raise ValueError(f"Missing required key '{key}' in {context}")
    return obj[key]


def load_suite(path: str | Path) -> Suite:
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    adapter_raw = raw.get("adapter") or {}
    stream_mode = adapter_raw.get("stream_mode")
    if stream_mode is not None:
        from agenttest.streaming import VALID_MODES

        if stream_mode not in VALID_MODES:
            raise ValueError(f"Invalid stream_mode '{stream_mode}', must be one of {sorted(VALID_MODES)}")

    adapter = AdapterConfig(
        type=adapter_raw.get("type", "http"),
        url=adapter_raw.get("url", ""),
        method=adapter_raw.get("method", "POST"),
        headers=adapter_raw.get("headers", {}) or {},
        timeout=float(adapter_raw.get("timeout", 30.0)),
        stream_mode=stream_mode,
    )

    if adapter.type == "http" and not adapter.url:
        raise ValueError("HTTP adapter requires adapter.url")

    tests: list[CaseSpec] = []
    for i, t in enumerate(raw.get("tests") or []):
        context = f"tests[{i}]"
        test_id = str(t.get("id") or f"test_{i+1}")
        name = str(t.get("name") or test_id)
        test_type = t.get("type", "single")
        tags = [str(x) for x in (t.get("tags") or [])]
        timeout = t.get("timeout")
        flaky = t.get("flaky_threshold")
        if flaky is not None:
            parse_flaky_threshold(str(flaky))  # validate early

        turns: list[TurnSpec] = []
        if test_type == "conversation":
            raw_turns = t.get("turns") or []
            if not raw_turns:
                raise ValueError(f"conversation test must have 'turns' in {context}")
            for j, turn in enumerate(raw_turns):
                user_msg = turn.get("user")
                if not user_msg:
                    raise ValueError(f"turn {j} must have 'user' in {context}")
                turn_assertions = turn.get("assertions") or []
                turns.append(TurnSpec(user=str(user_msg), assertions=turn_assertions))
            input_payload = None
            assertions: list[dict[str, Any]] = []
        else:
            input_payload = _require(t, "input", context)
            assertions = _require(t, "assertions", context)
            if not isinstance(assertions, list) or not assertions:
                raise ValueError(f"assertions must be a non-empty list in {context}")

        tests.append(
            CaseSpec(
                id=test_id,
                name=name,
                input=input_payload,
                assertions=assertions,
                tags=tags,
                timeout=float(timeout) if timeout is not None else None,
                flaky_threshold=str(flaky) if flaky is not None else None,
                type=test_type,
                turns=turns,
            )
        )

    if not tests:
        raise ValueError("Suite must define at least one test in 'tests'")

    return Suite(name=raw.get("name", path.stem), adapter=adapter, tests=tests)
