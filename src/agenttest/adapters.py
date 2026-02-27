from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

import requests

from agenttest.spec import AdapterConfig


@dataclass
class AdapterResponse:
    status_code: int
    text: str
    json: Any
    latency_ms: float
    headers: dict[str, str]


class HTTPAdapter:
    def __init__(self, config: AdapterConfig):
        self.config = config

    def call(self, payload: dict[str, Any], timeout: float | None = None) -> AdapterResponse:
        t0 = time.perf_counter()
        response = requests.request(
            method=self.config.method,
            url=self.config.url,
            headers={"content-type": "application/json", **self.config.headers},
            json=payload,
            timeout=timeout if timeout is not None else self.config.timeout,
        )
        latency_ms = (time.perf_counter() - t0) * 1000

        try:
            parsed = response.json()
        except json.JSONDecodeError:
            parsed = None

        return AdapterResponse(
            status_code=response.status_code,
            text=response.text,
            json=parsed,
            latency_ms=latency_ms,
            headers=dict(response.headers),
        )


def build_adapter(config: AdapterConfig):
    if config.type == "http":
        return HTTPAdapter(config)
    raise ValueError(f"Unsupported adapter type: {config.type}")
