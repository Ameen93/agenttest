from pathlib import Path

from agenttest.adapters import AdapterResponse
from agenttest.runner import RunOptions, Runner
from agenttest.spec import AdapterConfig, CaseSpec, Suite, TurnSpec


def _suite() -> Suite:
    return Suite(
        name="s",
        adapter=AdapterConfig(type="http", url="https://example.com"),
        tests=[
            CaseSpec(
                id="t1",
                name="t1",
                input={"message": "hi"},
                assertions=[
                    {"type": "status_code", "equals": 200},
                    {"type": "contains", "value": "hello"},
                ],
            )
        ],
    )


def test_runner_pass(tmp_path: Path):
    runner = Runner(suite=_suite(), state_dir=tmp_path)
    runner._execute_case = lambda test: AdapterResponse(  # type: ignore[method-assign]
        status_code=200,
        text="hello there",
        json={"meta": {"intent": "answer"}},
        latency_ms=100.0,
        headers={},
    )

    report = runner.run(RunOptions())
    assert report["summary"]["failed"] == 0
    assert report["tests"][0]["status"] == "passed"


def test_snapshot_change_non_strict_marks_changed_and_passes(tmp_path: Path):
    runner = Runner(suite=_suite(), state_dir=tmp_path)

    runner._execute_case = lambda test: AdapterResponse(  # type: ignore[method-assign]
        status_code=200,
        text="hello there",
        json={"meta": {"intent": "answer"}},
        latency_ms=100.0,
        headers={},
    )
    first = runner.run(RunOptions(strict_snapshots=False))
    assert first["tests"][0]["status"] == "passed"
    assert first["tests"][0]["snapshot_changed"] is False

    runner._execute_case = lambda test: AdapterResponse(  # type: ignore[method-assign]
        status_code=200,
        text="hello there v2",
        json={"meta": {"intent": "answer"}},
        latency_ms=100.0,
        headers={},
    )
    second = runner.run(RunOptions(strict_snapshots=False))
    assert second["tests"][0]["status"] == "passed"
    assert second["tests"][0]["snapshot_changed"] is True


def test_snapshot_change_strict_fails_with_diff(tmp_path: Path):
    runner = Runner(suite=_suite(), state_dir=tmp_path)

    runner._execute_case = lambda test: AdapterResponse(  # type: ignore[method-assign]
        status_code=200,
        text="hello there",
        json={"meta": {"intent": "answer"}},
        latency_ms=100.0,
        headers={},
    )
    runner.run(RunOptions(strict_snapshots=True))

    runner._execute_case = lambda test: AdapterResponse(  # type: ignore[method-assign]
        status_code=200,
        text="hello there changed",
        json={"meta": {"intent": "answer"}},
        latency_ms=100.0,
        headers={},
    )
    report = runner.run(RunOptions(strict_snapshots=True))
    t = report["tests"][0]

    assert t["status"] == "failed"
    assert "snapshot mismatch (strict mode)" in t["reason"]
    assert "snapshot diff summary:" in t["reason"]
    assert "--- baseline" in t["reason"]
    assert "+++ current" in t["reason"]


def test_response_body_in_report(tmp_path: Path):
    runner = Runner(suite=_suite(), state_dir=tmp_path)
    runner._execute_case = lambda test, **kw: AdapterResponse(  # type: ignore[method-assign]
        status_code=200,
        text="hello there",
        json=None,
        latency_ms=100.0,
        headers={},
    )
    report = runner.run(RunOptions())
    assert report["tests"][0]["response_body"] == "hello there"


def test_token_tracking(tmp_path: Path):
    runner = Runner(suite=_suite(), state_dir=tmp_path)
    runner._execute_case = lambda test, **kw: AdapterResponse(  # type: ignore[method-assign]
        status_code=200,
        text="hello there",
        json=None,
        latency_ms=100.0,
        headers={"x-usage-input-tokens": "50", "x-usage-output-tokens": "30"},
    )
    report = runner.run(RunOptions())
    assert report["tests"][0]["input_tokens"] == 50
    assert report["tests"][0]["output_tokens"] == 30
    assert report["summary"]["input_tokens"] == 50
    assert report["summary"]["output_tokens"] == 30


def test_flaky_threshold_pass(tmp_path: Path):
    suite = Suite(
        name="s",
        adapter=AdapterConfig(type="http", url="https://example.com"),
        tests=[
            CaseSpec(
                id="flaky1",
                name="flaky1",
                input={"message": "hi"},
                assertions=[{"type": "contains", "value": "hello"}],
                flaky_threshold="2/3",
            )
        ],
    )
    runner = Runner(suite=suite, state_dir=tmp_path)
    call_count = 0

    def _mock_execute(test, **kw):
        nonlocal call_count
        call_count += 1
        # Fail on attempt 2, pass on 1 and 3
        text = "hello" if call_count != 2 else "nope"
        return AdapterResponse(status_code=200, text=text, json=None, latency_ms=10.0, headers={})

    runner._execute_case = _mock_execute  # type: ignore[method-assign]
    report = runner.run(RunOptions())
    assert call_count == 3
    assert report["tests"][0]["status"] == "passed"
    assert "flaky 2/3" in report["tests"][0]["reason"]


def test_fail_fast(tmp_path: Path):
    suite = Suite(
        name="s",
        adapter=AdapterConfig(type="http", url="https://example.com"),
        tests=[
            CaseSpec(id="t1", name="t1", input={"m": "a"}, assertions=[{"type": "contains", "value": "nope"}]),
            CaseSpec(id="t2", name="t2", input={"m": "b"}, assertions=[{"type": "contains", "value": "hello"}]),
        ],
    )
    runner = Runner(suite=suite, state_dir=tmp_path)
    runner._execute_case = lambda test, **kw: AdapterResponse(  # type: ignore[method-assign]
        status_code=200, text="hello", json=None, latency_ms=10.0, headers={},
    )
    report = runner.run(RunOptions(fail_fast=True))
    # Should stop after first failure — only 1 test result
    assert len(report["tests"]) == 1
    assert report["tests"][0]["status"] == "failed"


def test_tags_order(tmp_path: Path):
    suite = Suite(
        name="s",
        adapter=AdapterConfig(type="http", url="https://example.com"),
        tests=[
            CaseSpec(id="t1", name="t1", input={"m": "a"}, assertions=[{"type": "status_code", "equals": 200}], tags=["slow"]),
            CaseSpec(id="t2", name="t2", input={"m": "b"}, assertions=[{"type": "status_code", "equals": 200}], tags=["smoke"]),
            CaseSpec(id="t3", name="t3", input={"m": "c"}, assertions=[{"type": "status_code", "equals": 200}], tags=["safety"]),
        ],
    )
    runner = Runner(suite=suite, state_dir=tmp_path)
    runner._execute_case = lambda test, **kw: AdapterResponse(  # type: ignore[method-assign]
        status_code=200, text="ok", json=None, latency_ms=10.0, headers={},
    )
    report = runner.run(RunOptions(tags_order=["smoke", "safety", "slow"]))
    ids = [t["id"] for t in report["tests"]]
    assert ids == ["t2", "t3", "t1"]


def test_conversation_test(tmp_path: Path):
    suite = Suite(
        name="s",
        adapter=AdapterConfig(type="http", url="https://example.com"),
        tests=[
            CaseSpec(
                id="conv1",
                name="conv1",
                type="conversation",
                turns=[
                    TurnSpec(user="Hi", assertions=[{"type": "contains", "value": "hello"}]),
                    TurnSpec(user="How are you?", assertions=[{"type": "contains", "value": "fine"}]),
                ],
            )
        ],
    )
    runner = Runner(suite=suite, state_dir=tmp_path)

    def _mock_execute(test, payload=None):
        msgs = payload.get("messages", []) if payload else []
        if len(msgs) == 1:
            text = "hello there"
        else:
            text = "I'm fine thanks"
        return AdapterResponse(
            status_code=200, text=text, json={"reply": text}, latency_ms=50.0, headers={},
        )

    runner._execute_case = _mock_execute  # type: ignore[method-assign]
    report = runner.run(RunOptions())
    assert report["tests"][0]["status"] == "passed"
    assert report["tests"][0]["reason"] == "all turns passed"
