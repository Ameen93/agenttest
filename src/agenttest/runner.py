from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from agenttest.adapters import AdapterResponse, build_adapter
from agenttest.assertions import evaluate_assertion
from agenttest.snapshots import compare_snapshots, load_snapshot, normalize_response, save_snapshot, snapshot_path
from agenttest.spec import CaseSpec, Suite, parse_flaky_threshold


@dataclass
class TestResult:
    id: str
    name: str
    status: str
    reason: str
    latency_ms: float
    status_code: int
    assertion_results: list[dict[str, Any]]
    response_body: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    snapshot_changed: bool = False


@dataclass
class RunOptions:
    strict_snapshots: bool = False
    tags: set[str] | None = None
    reruns: int = 0
    tags_order: list[str] | None = None
    fail_fast: bool = False


class Runner:
    def __init__(self, suite: Suite, state_dir: Path):
        self.suite = suite
        self.state_dir = state_dir
        self.adapter = build_adapter(suite.adapter)

    def _test_selected(self, test: CaseSpec, tags: set[str] | None) -> bool:
        if not tags:
            return True
        return bool(set(test.tags) & tags)

    def _execute_case(self, test: CaseSpec, payload: dict[str, Any] | None = None) -> AdapterResponse:
        return self.adapter.call(payload if payload is not None else test.input, timeout=test.timeout)

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

    def _build_result(self, test: CaseSpec, response: AdapterResponse, passed: bool, reason: str, details: list[dict[str, Any]], options: RunOptions) -> TestResult:
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

        input_tokens = int(response.headers.get("x-usage-input-tokens", 0))
        output_tokens = int(response.headers.get("x-usage-output-tokens", 0))

        return TestResult(
            id=test.id,
            name=test.name,
            status="passed" if passed else "failed",
            reason=reason,
            latency_ms=response.latency_ms,
            status_code=response.status_code,
            assertion_results=details,
            response_body=response.text[:2000],
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            snapshot_changed=snapshot_changed,
        )

    def _run_standard(self, test: CaseSpec, options: RunOptions) -> TestResult | None:
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
            last_result = self._build_result(test, response, passed, reason, details, options)

            if last_result.status == "passed":
                break

        return last_result

    def _run_flaky(self, test: CaseSpec, options: RunOptions) -> TestResult:
        required, total = parse_flaky_threshold(test.flaky_threshold)
        pass_count = 0
        last_result: TestResult | None = None

        for _ in range(total):
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
            last_result = self._build_result(test, response, passed, reason, details, options)
            if passed:
                pass_count += 1

        overall = pass_count >= required
        if last_result is None:
            return TestResult(
                id=test.id,
                name=test.name,
                status="failed",
                reason="all attempts errored",
                latency_ms=0.0,
                status_code=0,
                assertion_results=[],
            )

        last_result.status = "passed" if overall else "failed"
        last_result.reason = f"flaky {pass_count}/{total} (need {required}/{total})"
        return last_result

    def _extract_assistant_text(self, response: AdapterResponse) -> str:
        """Extract assistant reply text from response, trying common JSON keys."""
        if response.json and isinstance(response.json, dict):
            for key in ("reply", "content", "message"):
                val = response.json.get(key)
                if isinstance(val, str):
                    return val
        return response.text

    def _execute_conversation(self, test: CaseSpec, options: RunOptions) -> TestResult:
        messages: list[dict[str, str]] = []
        all_details: list[dict[str, Any]] = []
        total_latency = 0.0
        last_response: AdapterResponse | None = None
        last_status_code = 0

        for i, turn in enumerate(test.turns):
            messages.append({"role": "user", "content": turn.user})
            try:
                response = self._execute_case(test, payload={"messages": messages})
            except Exception as e:
                return TestResult(
                    id=test.id,
                    name=test.name,
                    status="failed",
                    reason=f"turn {i} adapter error: {e}",
                    latency_ms=total_latency,
                    status_code=0,
                    assertion_results=all_details,
                )

            last_response = response
            last_status_code = response.status_code
            total_latency += response.latency_ms
            assistant_text = self._extract_assistant_text(response)
            messages.append({"role": "assistant", "content": assistant_text})

            for assertion in turn.assertions:
                ok, detail = evaluate_assertion(
                    assertion,
                    status_code=response.status_code,
                    body_text=assistant_text,
                    body_json=response.json,
                    latency_ms=response.latency_ms,
                )
                all_details.append({"turn": i, "assertion": assertion, "ok": ok, "detail": detail})
                if not ok:
                    return TestResult(
                        id=test.id,
                        name=test.name,
                        status="failed",
                        reason=f"turn {i}: {detail}",
                        latency_ms=total_latency,
                        status_code=last_status_code,
                        assertion_results=all_details,
                        response_body=response.text[:2000],
                    )

        return TestResult(
            id=test.id,
            name=test.name,
            status="passed",
            reason="all turns passed",
            latency_ms=total_latency,
            status_code=last_status_code,
            assertion_results=all_details,
            response_body=last_response.text[:2000] if last_response else "",
            input_tokens=int(last_response.headers.get("x-usage-input-tokens", 0)) if last_response else 0,
            output_tokens=int(last_response.headers.get("x-usage-output-tokens", 0)) if last_response else 0,
        )

    def _sort_by_tags(self, tests: list[CaseSpec], tags_order: list[str]) -> list[CaseSpec]:
        priority = {tag: i for i, tag in enumerate(tags_order)}
        sentinel = len(tags_order)

        def key(test: CaseSpec) -> int:
            return min((priority.get(t, sentinel) for t in test.tags), default=sentinel)

        return sorted(tests, key=key)

    def run(self, options: RunOptions) -> dict[str, Any]:
        started = time.perf_counter()
        test_results: list[TestResult] = []

        tests = [t for t in self.suite.tests if self._test_selected(t, options.tags)]
        if options.tags_order:
            tests = self._sort_by_tags(tests, options.tags_order)

        for test in tests:
            if test.type == "conversation":
                result = self._execute_conversation(test, options)
            elif test.flaky_threshold:
                result = self._run_flaky(test, options)
            else:
                result = self._run_standard(test, options)

            if result is not None:
                test_results.append(result)
                if options.fail_fast and result.status == "failed":
                    break

        duration_ms = (time.perf_counter() - started) * 1000
        total = len(test_results)
        passed = sum(1 for t in test_results if t.status == "passed")
        failed = total - passed
        total_input_tokens = sum(t.input_tokens for t in test_results)
        total_output_tokens = sum(t.output_tokens for t in test_results)

        summary: dict[str, Any] = {
            "total": total,
            "passed": passed,
            "failed": failed,
            "duration_ms": round(duration_ms, 2),
        }
        if total_input_tokens or total_output_tokens:
            summary["input_tokens"] = total_input_tokens
            summary["output_tokens"] = total_output_tokens

        return {
            "suite": self.suite.name,
            "summary": summary,
            "tests": [asdict(x) for x in test_results],
        }
