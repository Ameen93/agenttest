from pathlib import Path

from agenttest.spec import load_suite


def test_load_suite(tmp_path: Path):
    suite_file = tmp_path / "suite.yaml"
    suite_file.write_text(
        """
name: sample
adapter:
  type: http
  url: https://example.com/agent
tests:
  - id: t1
    input: {message: hi}
    assertions:
      - type: status_code
        equals: 200
""",
        encoding="utf-8",
    )

    suite = load_suite(suite_file)
    assert suite.name == "sample"
    assert suite.adapter.url == "https://example.com/agent"
    assert suite.tests[0].id == "t1"
