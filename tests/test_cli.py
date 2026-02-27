from pathlib import Path

from agenttest import cli


def test_cmd_init_writes_quickstart_suite(tmp_path: Path):
    out = tmp_path / "agenttest.suite.yaml"

    exit_code = cli.main(["init", "--path", str(out)])

    assert exit_code == 0
    content = out.read_text(encoding="utf-8")
    assert "name: quickstart-suite" in content
    assert "id: greeting_smoke" in content
    assert "id: json_contract" in content


def test_cmd_init_refuses_overwrite_without_force(tmp_path: Path):
    out = tmp_path / "agenttest.suite.yaml"
    out.write_text("name: existing\n", encoding="utf-8")

    exit_code = cli.main(["init", "--path", str(out)])

    assert exit_code == 1
    assert out.read_text(encoding="utf-8") == "name: existing\n"


def test_cmd_init_overwrites_with_force(tmp_path: Path):
    out = tmp_path / "agenttest.suite.yaml"
    out.write_text("name: existing\n", encoding="utf-8")

    exit_code = cli.main(["init", "--path", str(out), "--force"])

    assert exit_code == 0
    assert "quickstart-suite" in out.read_text(encoding="utf-8")
