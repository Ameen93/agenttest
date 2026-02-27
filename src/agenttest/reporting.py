from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring


def write_json_report(report_dir: Path, report: dict) -> tuple[Path, Path]:
    report_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_path = report_dir / f"run-{ts}.json"
    last_path = report_dir / "last_run.json"
    payload = json.dumps(report, indent=2, ensure_ascii=False)
    run_path.write_text(payload, encoding="utf-8")
    last_path.write_text(payload, encoding="utf-8")
    return run_path, last_path


def write_junit(path: Path, report: dict) -> None:
    testsuite = Element(
        "testsuite",
        name=report.get("suite", "agenttest"),
        tests=str(report["summary"]["total"]),
        failures=str(report["summary"]["failed"]),
        time=f"{report['summary']['duration_ms'] / 1000:.3f}",
    )

    for t in report["tests"]:
        case = SubElement(
            testsuite,
            "testcase",
            name=t["name"],
            classname=report.get("suite", "agenttest"),
            time=f"{t['latency_ms'] / 1000:.3f}",
        )
        if t["status"] != "passed":
            failure = SubElement(case, "failure", message=t.get("reason", "failed"))
            failure.text = t.get("reason", "failed")

    xml = tostring(testsuite, encoding="unicode")
    path.write_text('<?xml version="1.0" encoding="UTF-8"?>\n' + xml, encoding="utf-8")
