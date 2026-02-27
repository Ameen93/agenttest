from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from agenttest.adapters import AdapterResponse, build_adapter
from agenttest.assertions import evaluate_assertion
from agenttest.snapshots import compare_snapshots, load_snapshot, normalize_response, save_snapshot, snapshot_path
from agenttest.spec import CaseSpec, Suite


@dataclass
class TestResult:
    id: str
    name: str
    status: str
    reason: str
    latency_ms: float
    status_code: int
    assertion_results: list[dict[str, Any]]
    snapshot_changed: bool = False


@dataclass
class RunOptions:
    strict_snapshots: bool = False
    tags: set[str] | None = None
    reruns: int = 0


class Runner:
    def __init__(self, suite: Suite, state_dir: Path):
        self.suite = suite
        self.state_dir = state_dir
        self.adapter = build_adapter(suite.adapter)

    def _test_selected(self, test: CaseSpec, tags: set[str] | None) -> bool:
        if not tags:
            return True
        return bool(set(test.tags) & tags)

    def _execute_case(self, test: CaseSpec) -> AdapterResponse:
        return self.adapter.call(test.input, timeout=test.timeout)

    def _assert_case(self, test: CaseSpec, response: AdapterResponse) -> tuple[bool, str, list[dict[str, Any]]]:
        details: list[dict[str, Any]] = []
        for assertion in test.assertions:
            ok, detail = evaluate_assertion(
                assertion,
                status_code=response.status_code,
                body_text=response.text,
                body_json=response.json,
                latency_ms=response.latency_ms,
            )
            details.append({"assertion": assertion, "ok": ok, "detail": detail})
            if not ok:
                return False, detail, details
        return True, "all assertions passed", details

    def run(self, options: RunOptions) -> dict[str, Any]:
        started = time.perf_counter()
        test_results: list[TestResult] = []

        for test in self.suite.tests:
            if not self._test_selected(test, options.tags):
                continue

            attempts = max(1, options.reruns + 1)
            last_result: TestResult | None = None

            for _ in range(attempts):
                try:
                    response = self._execute_case(test)
                except Exception as e:
                    last_result = TestResult(
                        id=test.id,
                        name=test.name,
                        status="failed",
                        reason=f"adapter error: {e}",
                        latency_ms=0.0,
                        status_code=0,
                        assertion_results=[],
                    )
                    continue

                passed, reason, details = self._assert_case(test, response)
                snapshot_changed = False

                if passed:
                    snap_file = snapshot_path(self.state_dir, self.suite.name, test.id)
                    current = normalize_response(
                        {
                            "status_code": response.status_code,
                            "text": response.text,
                            "json": response.json,
                        }
                    )
                    baseline = load_snapshot(snap_file)
                    if baseline is None:
                        save_snapshot(snap_file, current)
                    else:
                        same, diff = compare_snapshots(baseline, current)
                        if not same:
                            snapshot_changed = True
                            if options.strict_snapshots:
                                passed = False
                                reason = f"snapshot mismatch (strict mode)\n{diff}"
                            else:
                                save_snapshot(snap_file, current)

                last_result = TestResult(
                    id=test.id,
                    name=test.name,
                    status="passed" if passed else "failed",
                    reason=reason,
                    latency_ms=response.latency_ms,
                    status_code=response.status_code,
                    assertion_results=details,
                    snapshot_changed=snapshot_changed,
                )

                if passed:
                    break

            if last_result is not None:
                test_results.append(last_result)

        duration_ms = (time.perf_counter() - started) * 1000
        total = len(test_results)
        passed = sum(1 for t in test_results if t.status == "passed")
        failed = total - passed

        return {
            "suite": self.suite.name,
            "summary": {
                "total": total,
                "passed": passed,
                "failed": failed,
                "duration_ms": round(duration_ms, 2),
            },
            "tests": [asdict(x) for x in test_results],
        }
