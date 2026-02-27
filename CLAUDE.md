# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

AgentTest — a pytest-style CLI for testing AI agent HTTP endpoints. Define test suites in YAML, run assertions against agent responses, and get JSON/JUnit reports.

## Stack

- Python 3.12+, managed with **uv**
- Dependencies: PyYAML, requests
- Dev dependency: pytest
- Build backend: hatchling
- Entry point: `agenttest` CLI via `agenttest.cli:main`

## Commands

```bash
uv sync --dev          # install deps (or: make sync)
uv run pytest -q       # run unit tests (or: make test)
uv run pytest tests/test_assertions.py::test_contains  # run a single test
make smoke             # mock server + CLI smoke suite + cleanup
bash scripts/run_local_ci.sh   # full local CI: sync + tests + smoke (or: make ci)
```

## Architecture

The pipeline is: **YAML suite** → `spec.load_suite()` → `Runner` → `Adapter.call()` → `evaluate_assertion()` → report.

Key modules in `src/agenttest/`:

- **spec.py** — Parses YAML into `Suite` / `CaseSpec` / `AdapterConfig` dataclasses
- **adapters.py** — `HTTPAdapter` sends requests to agent endpoints; `build_adapter()` factory selects adapter by type. New adapter types plug in here.
- **assertions.py** — `evaluate_assertion()` dispatches by assertion `type` string (contains, not_contains, regex, json_path_equals, status_code, max_latency_ms). `get_path()` resolves dotted JSON paths.
- **runner.py** — `Runner.run()` iterates test cases, applies tag filtering, handles reruns, and manages snapshot comparison. Returns a report dict.
- **snapshots.py** — Baseline snapshot storage in `.agenttest/snapshots/<suite>/<test_id>.json`. Compares normalized responses with unified diff.
- **reporting.py** — Writes timestamped JSON reports to `.agenttest/reports/` and optional JUnit XML.
- **cli.py** — argparse CLI with `init`, `run`, `report` subcommands. URL override via `--base-url` or `AGENTTEST_BASE_URL` env var.

## Suite YAML format

Suites define an `adapter` block (type, url, method, headers, timeout) and a `tests` list. Each test has `id`, `input` (JSON payload), `assertions`, optional `tags` and `timeout`.

## Other directories

- **ops/** — Separate lightweight Jira-style ops board (Python server + HTML/JS SPA + SQLite). Not part of the core library. Run with `make ops`.
- **scripts/** — `mock_agent_server.py` (test fixture), `run_local_ci.sh`, `run_ops_board.sh`
- **examples/** — Sample suite YAML files (quickstart, CI smoke)
- **artifacts/** — CI report outputs (JSON + JUnit XML)
