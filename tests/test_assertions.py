from unittest.mock import MagicMock, patch

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


def test_min_latency_ms_pass():
    ok, detail = evaluate_assertion(
        {"type": "min_latency_ms", "ge": 100},
        status_code=200,
        body_text="",
        body_json=None,
        latency_ms=150,
    )
    assert ok
    assert "150.0ms >= 100.0ms" in detail


def test_min_latency_ms_fail():
    ok, detail = evaluate_assertion(
        {"type": "min_latency_ms", "ge": 200},
        status_code=200,
        body_text="",
        body_json=None,
        latency_ms=150,
    )
    assert not ok
    assert "150.0ms >= 200.0ms" in detail


def test_json_path_equals():
    ok, _ = evaluate_assertion(
        {"type": "json_path_equals", "path": "meta.intent", "equals": "answer"},
        status_code=200,
        body_text="",
        body_json={"meta": {"intent": "answer"}},
        latency_ms=50,
    )
    assert ok


def _mock_anthropic(score: float, reasoning: str = "good"):
    """Create a mock anthropic module with a fake messages.create response."""
    import json

    mock_module = MagicMock()
    mock_content = MagicMock()
    mock_content.text = json.dumps({"score": score, "reasoning": reasoning})
    mock_message = MagicMock()
    mock_message.content = [mock_content]
    mock_module.Anthropic.return_value.messages.create.return_value = mock_message
    return mock_module


def test_llm_judge_pass():
    mock_mod = _mock_anthropic(0.9, "relevant and accurate")
    with patch.dict("sys.modules", {"anthropic": mock_mod}):
        ok, detail = evaluate_assertion(
            {"type": "llm_judge", "criteria": "Is the response helpful?", "pass_threshold": 0.7},
            status_code=200,
            body_text="Here is a helpful answer.",
            body_json=None,
            latency_ms=100,
        )
    assert ok
    assert "score=0.90" in detail


def test_llm_judge_fail():
    mock_mod = _mock_anthropic(0.3, "not relevant")
    with patch.dict("sys.modules", {"anthropic": mock_mod}):
        ok, detail = evaluate_assertion(
            {"type": "llm_judge", "criteria": "Is the response helpful?", "pass_threshold": 0.8},
            status_code=200,
            body_text="I don't know",
            body_json=None,
            latency_ms=100,
        )
    assert not ok
    assert "score=0.30" in detail
