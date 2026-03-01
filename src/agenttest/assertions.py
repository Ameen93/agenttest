from __future__ import annotations

import json
import re
from typing import Any


class AssertionErrorDetail(Exception):
    pass


def get_path(data: Any, path: str) -> Any:
    """Resolve simple dotted paths, supports indexes e.g. items.0.name"""
    if path in ("", "."):
        return data

    current = data
    for part in path.split("."):
        if isinstance(current, list):
            idx = int(part)
            current = current[idx]
        elif isinstance(current, dict):
            if part not in current:
                raise AssertionErrorDetail(f"Path '{path}' not found (missing '{part}')")
            current = current[part]
        else:
            raise AssertionErrorDetail(f"Cannot resolve '{part}' in path '{path}'")
    return current


def evaluate_assertion(assertion: dict[str, Any], *, status_code: int, body_text: str, body_json: Any, latency_ms: float) -> tuple[bool, str]:
    atype = assertion.get("type")
    if not atype:
        return False, "assertion missing type"

    try:
        if atype == "contains":
            target = body_text if "path" not in assertion else str(get_path(body_json, assertion["path"]))
            needle = str(assertion["value"])
            ok = needle in target
            return ok, f"contains '{needle}'"

        if atype == "not_contains":
            target = body_text if "path" not in assertion else str(get_path(body_json, assertion["path"]))
            needle = str(assertion["value"])
            ok = needle not in target
            return ok, f"not_contains '{needle}'"

        if atype == "regex":
            pattern = assertion["pattern"]
            target = body_text if "path" not in assertion else str(get_path(body_json, assertion["path"]))
            ok = re.search(pattern, target) is not None
            return ok, f"regex /{pattern}/"

        if atype == "json_path_equals":
            actual = get_path(body_json, assertion["path"])
            expected = assertion.get("equals")
            ok = actual == expected
            return ok, f"json_path_equals {assertion['path']} == {expected!r} (actual={actual!r})"

        if atype == "status_code":
            expected = int(assertion["equals"])
            ok = status_code == expected
            return ok, f"status_code == {expected} (actual={status_code})"

        if atype == "max_latency_ms":
            maximum = float(assertion["le"])
            ok = latency_ms <= maximum
            return ok, f"latency {latency_ms:.1f}ms <= {maximum:.1f}ms"

        if atype == "min_latency_ms":
            minimum = float(assertion["ge"])
            ok = latency_ms >= minimum
            return ok, f"latency {latency_ms:.1f}ms >= {minimum:.1f}ms"

        if atype == "llm_judge":
            return _evaluate_llm_judge(assertion, body_text)

        return False, f"unknown assertion type '{atype}'"

    except KeyError as e:
        return False, f"assertion '{atype}' missing key {e}"
    except (AssertionErrorDetail, IndexError, ValueError, TypeError) as e:
        return False, f"assertion '{atype}' error: {e}"


def _evaluate_llm_judge(assertion: dict[str, Any], body_text: str) -> tuple[bool, str]:
    try:
        import anthropic
    except ImportError:
        return False, "llm_judge requires 'anthropic' package (install with: pip install agenttest[llm-judge])"

    criteria = assertion.get("criteria", "")
    if not criteria:
        return False, "llm_judge assertion missing 'criteria'"

    model = assertion.get("model", "claude-haiku-4-5-20251001")
    pass_threshold = float(assertion.get("pass_threshold", 0.8))

    judge_prompt = (
        "You are an AI judge evaluating a response. Score the response on this criteria:\n\n"
        f"Criteria: {criteria}\n\n"
        f"Response to evaluate:\n{body_text}\n\n"
        'Respond with ONLY a JSON object: {"score": <0.0-1.0>, "reasoning": "<brief explanation>"}'
    )

    try:
        client = anthropic.Anthropic()
        message = client.messages.create(
            model=model,
            max_tokens=256,
            messages=[{"role": "user", "content": judge_prompt}],
        )
        raw = message.content[0].text.strip()
        result = json.loads(raw)
        score = float(result["score"])
        reasoning = result.get("reasoning", "")
        ok = score >= pass_threshold
        return ok, f"llm_judge score={score:.2f} (threshold={pass_threshold}) reasoning={reasoning}"
    except Exception as e:
        return False, f"llm_judge error: {e}"
