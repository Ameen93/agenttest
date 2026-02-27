from __future__ import annotations

import difflib
import json
from pathlib import Path
from typing import Any


def snapshot_path(root: Path, suite_name: str, test_id: str) -> Path:
    return root / "snapshots" / suite_name / f"{test_id}.json"


def normalize_response(response_obj: dict[str, Any]) -> dict[str, Any]:
    return {
        "status_code": response_obj.get("status_code"),
        "json": response_obj.get("json"),
        "text": response_obj.get("text"),
    }


def load_snapshot(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_snapshot(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def _summarize_diff_lines(diff_text: str) -> tuple[int, int]:
    added = 0
    removed = 0
    for line in diff_text.splitlines():
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("+"):
            added += 1
        elif line.startswith("-"):
            removed += 1
    return added, removed


def compare_snapshots(old: dict[str, Any], new: dict[str, Any], max_chars: int = 4000) -> tuple[bool, str]:
    old_str = json.dumps(old, indent=2, ensure_ascii=False, sort_keys=True).splitlines(keepends=True)
    new_str = json.dumps(new, indent=2, ensure_ascii=False, sort_keys=True).splitlines(keepends=True)
    if old_str == new_str:
        return True, ""

    raw_diff = "".join(difflib.unified_diff(old_str, new_str, fromfile="baseline", tofile="current", n=3))
    added, removed = _summarize_diff_lines(raw_diff)
    header = f"snapshot diff summary: +{added} / -{removed} lines\n"

    if len(raw_diff) > max_chars:
        suffix = f"\n... diff truncated to {max_chars} chars (full diff omitted)"
        diff_body = raw_diff[: max_chars - len(suffix)] + suffix
    else:
        diff_body = raw_diff

    return False, header + diff_body
