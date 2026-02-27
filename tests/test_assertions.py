from agenttest.assertions import evaluate_assertion


def test_contains_and_status_code():
    ok, _ = evaluate_assertion(
        {"type": "contains", "value": "hello"},
        status_code=200,
        body_text="hello world",
        body_json={"meta": {"intent": "answer"}},
        latency_ms=120,
    )
    assert ok

    ok, _ = evaluate_assertion(
        {"type": "status_code", "equals": 200},
        status_code=200,
        body_text="hello world",
        body_json={"meta": {"intent": "answer"}},
        latency_ms=120,
    )
    assert ok


def test_json_path_equals():
    ok, _ = evaluate_assertion(
        {"type": "json_path_equals", "path": "meta.intent", "equals": "answer"},
        status_code=200,
        body_text="",
        body_json={"meta": {"intent": "answer"}},
        latency_ms=50,
    )
    assert ok
