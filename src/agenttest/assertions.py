from __future__ import annotations

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

        return False, f"unknown assertion type '{atype}'"

    except KeyError as e:
        return False, f"assertion '{atype}' missing key {e}"
    except (AssertionErrorDetail, IndexError, ValueError, TypeError) as e:
        return False, f"assertion '{atype}' error: {e}"
