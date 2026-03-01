from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from agenttest.reporting import write_json_report, write_junit
from agenttest.runner import RunOptions, Runner
from agenttest.spec import load_suite

STATE_DIR = Path(".agenttest")

EXAMPLE_SUITE = """name: quickstart-suite
adapter:
  type: http
  url: http://127.0.0.1:18080/agent
  method: POST
  timeout: 10

tests:
  - id: greeting_smoke
    name: Greeting includes hello + safety
    tags: [quickstart, smoke]
    input:
      message: "Say hello and mention safety"
    assertions:
      - type: status_code
        equals: 200
      - type: contains
        value: "hello"
      - type: regex
        pattern: "(?i)safety"
      - type: max_latency_ms
        le: 2000

  - id: json_contract
    name: Response shape is stable for CI and local checks
    tags: [quickstart, contract]
    input:
      message: "Return a safe answer"
    assertions:
      - type: status_code
        equals: 200
      - type: json_path_equals
        path: meta.intent
        equals: "answer"
      - type: not_contains
        value: "traceback"
"""


def _print_run(report: dict) -> None:
    summary = report["summary"]
    print(f"\nSuite: {report['suite']}")
    for t in report["tests"]:
        icon = "✅" if t["status"] == "passed" else "❌"
        snap_note = " (snapshot changed)" if t.get("snapshot_changed") else ""
        print(f"{icon} {t['id']} - {t['reason']}{snap_note} [{t['latency_ms']:.1f}ms]")
    line = (
        f"\nSummary: total={summary['total']} passed={summary['passed']} "
        f"failed={summary['failed']} duration={summary['duration_ms']:.1f}ms"
    )
    if summary.get("input_tokens") or summary.get("output_tokens"):
        line += f"\nTokens: input={summary.get('input_tokens', 0)} output={summary.get('output_tokens', 0)}"
    print(line)


def cmd_init(args: argparse.Namespace) -> int:
    path = Path(args.path)
    if path.exists() and not args.force:
        print(f"Refusing to overwrite existing file: {path}")
        return 1
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(EXAMPLE_SUITE, encoding="utf-8")
    print(f"Created example suite: {path}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    suite = load_suite(args.suite)

    if args.base_url:
        suite.adapter.url = args.base_url
    elif os.getenv("AGENTTEST_BASE_URL"):
        suite.adapter.url = os.environ["AGENTTEST_BASE_URL"]

    tags = set(args.tags.split(",")) if args.tags else None
    tags_order = args.tags_order.split(",") if args.tags_order else None

    runner = Runner(suite=suite, state_dir=STATE_DIR)
    report = runner.run(
        RunOptions(
            strict_snapshots=args.strict_snapshots,
            tags=tags,
            reruns=args.reruns,
            tags_order=tags_order,
            fail_fast=args.fail_fast,
        )
    )

    _print_run(report)
    report_dir = STATE_DIR / "reports"
    run_path, _last = write_json_report(report_dir, report)
    print(f"JSON report: {run_path}")

    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"CI JSON: {out}")

    if args.junit_out:
        junit_path = Path(args.junit_out)
        junit_path.parent.mkdir(parents=True, exist_ok=True)
        write_junit(junit_path, report)
        print(f"JUnit XML: {junit_path}")

    return 0 if report["summary"]["failed"] == 0 else 2


def cmd_report_last(_args: argparse.Namespace) -> int:
    path = STATE_DIR / "reports" / "last_run.json"
    if not path.exists():
        print("No prior run found.")
        return 1
    report = json.loads(path.read_text(encoding="utf-8"))
    _print_run(report)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agenttest", description="Test runner for AI agent endpoints")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Generate example suite")
    p_init.add_argument("--path", default="agenttest.suite.yaml", help="Output suite file path")
    p_init.add_argument("--force", action="store_true", help="Overwrite if exists")
    p_init.set_defaults(func=cmd_init)

    p_run = sub.add_parser("run", help="Run a suite")
    p_run.add_argument("suite", help="Path to suite YAML")
    p_run.add_argument("--tags", help="Comma-separated tags filter (e.g. safety,smoke)")
    p_run.add_argument("--strict-snapshots", action="store_true", help="Fail when baseline snapshot changes")
    p_run.add_argument("--json-out", help="Write JSON output to a specific file")
    p_run.add_argument("--junit-out", help="Write JUnit XML output")
    p_run.add_argument("--base-url", help="Override adapter URL (or use AGENTTEST_BASE_URL)")
    p_run.add_argument("--reruns", type=int, default=0, help="Retry failing tests N additional times")
    p_run.add_argument("--tags-order", help="Comma-separated tag priority for test ordering (e.g. smoke,safety)")
    p_run.add_argument("--fail-fast", action="store_true", help="Stop on first test failure")
    p_run.set_defaults(func=cmd_run)

    p_report = sub.add_parser("report", help="Report commands")
    p_report.add_argument("--last", action="store_true", help="Show latest run summary")
    p_report.set_defaults(func=cmd_report_last)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "report" and not args.last:
        parser.error("report currently supports only --last")

    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
