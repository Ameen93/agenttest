from pathlib import Path

from agenttest.adapters import AdapterResponse
from agenttest.runner import RunOptions, Runner
from agenttest.spec import AdapterConfig, CaseSpec, Suite


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
