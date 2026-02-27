from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class CaseSpec:
    id: str
    name: str
    input: dict[str, Any]
    assertions: list[dict[str, Any]]
    tags: list[str] = field(default_factory=list)
    timeout: float | None = None


@dataclass
class AdapterConfig:
    type: str = "http"
    url: str = ""
    method: str = "POST"
    headers: dict[str, str] = field(default_factory=dict)
    timeout: float = 30.0


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
    adapter = AdapterConfig(
        type=adapter_raw.get("type", "http"),
        url=adapter_raw.get("url", ""),
        method=adapter_raw.get("method", "POST"),
        headers=adapter_raw.get("headers", {}) or {},
        timeout=float(adapter_raw.get("timeout", 30.0)),
    )

    if adapter.type == "http" and not adapter.url:
        raise ValueError("HTTP adapter requires adapter.url")

    tests: list[CaseSpec] = []
    for i, t in enumerate(raw.get("tests") or []):
        context = f"tests[{i}]"
        test_id = str(t.get("id") or f"test_{i+1}")
        name = str(t.get("name") or test_id)
        input_payload = _require(t, "input", context)
        assertions = _require(t, "assertions", context)
        if not isinstance(assertions, list) or not assertions:
            raise ValueError(f"assertions must be a non-empty list in {context}")
        tags = [str(x) for x in (t.get("tags") or [])]
        timeout = t.get("timeout")
        tests.append(
            CaseSpec(
                id=test_id,
                name=name,
                input=input_payload,
                assertions=assertions,
                tags=tags,
                timeout=float(timeout) if timeout is not None else None,
            )
        )

    if not tests:
        raise ValueError("Suite must define at least one test in 'tests'")

    return Suite(name=raw.get("name", path.stem), adapter=adapter, tests=tests)
