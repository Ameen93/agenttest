from agenttest.streaming import parse_sse, parse_ndjson, parse_ai_sdk_ui


def test_parse_sse_basic():
    raw = "data: Hello\ndata:  world\ndata: [DONE]\n"
    assert parse_sse(raw) == "Hello world"


def test_parse_sse_empty():
    assert parse_sse("") == ""
    assert parse_sse("event: ping\n") == ""


def test_parse_ndjson_delta_content():
    raw = '{"delta": {"content": "Hello"}}\n{"delta": {"content": " world"}}\n'
    assert parse_ndjson(raw) == "Hello world"


def test_parse_ndjson_text_field():
    raw = '{"text": "Hello"}\n{"text": " there"}\n'
    assert parse_ndjson(raw) == "Hello there"


def test_parse_ndjson_skips_invalid():
    raw = 'not json\n{"text": "ok"}\n'
    assert parse_ndjson(raw) == "ok"


def test_parse_ai_sdk_ui():
    raw = '0:"Hello"\n0:" world"\n'
    assert parse_ai_sdk_ui(raw) == "Hello world"


def test_parse_ai_sdk_ui_with_escapes():
    raw = '0:"line1\\nline2"\n'
    assert parse_ai_sdk_ui(raw) == "line1\nline2"


def test_parse_ai_sdk_ui_ignores_non_text():
    raw = '2:[{"toolName":"search"}]\n0:"result"\n'
    assert parse_ai_sdk_ui(raw) == "result"
