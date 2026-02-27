# AgentTest

**pytest for AI agent endpoints.** Define test suites in YAML, run them against any HTTP endpoint, get deterministic pass/fail results with snapshot regression tracking.

[![CI](https://github.com/Ameen93/agenttest/actions/workflows/ci.yml/badge.svg)](https://github.com/Ameen93/agenttest/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/agenttest)](https://pypi.org/project/agenttest/)
[![Python](https://img.shields.io/pypi/pyversions/agenttest)](https://pypi.org/project/agenttest/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

Most AI evaluation tools require SDK instrumentation — you have to modify your agent's source code to test it. AgentTest takes a different approach: **test your agent from the outside, over HTTP, exactly as it runs in production.** Write YAML files, commit them alongside your code, run them in CI.

## Install

```bash
pip install agenttest
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv add agenttest
```

## Quickstart

**1. Generate a starter test suite:**

```bash
agenttest init
```

This creates `agenttest.suite.yaml` in your current directory.

**2. Edit it to point at your agent:**

```yaml
name: my-agent-tests
adapter:
  type: http
  url: http://localhost:8000/agent
  method: POST
  timeout: 10

tests:
  - id: greeting
    name: Agent greets the user
    tags: [smoke]
    input:
      message: "Hello"
    assertions:
      - type: status_code
        equals: 200
      - type: contains
        value: "hello"
      - type: max_latency_ms
        le: 2000
```

**3. Run it:**

```bash
agenttest run agenttest.suite.yaml
```

```
=== AgentTest Results ===
Suite: my-agent-tests
Tests: 1 passed, 0 failed (1 total)
Duration: 142ms
```

## Assertions

Six assertion types cover the deterministic layer of agent testing:

| Type | What it checks | Example |
|---|---|---|
| `status_code` | HTTP status code | `equals: 200` |
| `contains` | Substring in response body | `value: "hello"` |
| `not_contains` | Substring absent from response | `value: "traceback"` |
| `regex` | Regex match on response body | `pattern: "(?i)safe\|policy"` |
| `json_path_equals` | Dotted-path JSON value | `path: meta.intent`, `equals: "answer"` |
| `max_latency_ms` | Response time ceiling | `le: 3000` |

## Snapshot Testing

AgentTest records baseline snapshots of passing responses. On subsequent runs, it detects when your agent's output drifts:

```bash
# Normal mode: updates snapshot, marks as changed
agenttest run suite.yaml

# Strict mode: fails the test on any snapshot drift
agenttest run suite.yaml --strict-snapshots
```

Snapshots are stored in `.agenttest/snapshots/<suite>/<test_id>.json` and can be committed to git for team-wide regression tracking.

## Tag Filtering

Run a subset of tests by tag:

```bash
agenttest run suite.yaml --tags smoke,safety
```

A test runs if it has *any* of the specified tags.

## Reruns

Retry failing tests to handle flaky agent responses:

```bash
agenttest run suite.yaml --reruns 2
```

## Reports

```bash
# JSON report (for CI pipelines)
agenttest run suite.yaml --json-out report.json

# JUnit XML (for GitHub Actions, Jenkins, etc.)
agenttest run suite.yaml --junit-out report.xml

# Re-print last run's summary without re-running
agenttest report --last
```

## URL Override

Override the suite's endpoint URL without editing YAML:

```bash
# Via flag
agenttest run suite.yaml --base-url http://staging:8000/agent

# Via environment variable
export AGENTTEST_BASE_URL=http://staging:8000/agent
agenttest run suite.yaml
```

Priority: `--base-url` flag > `AGENTTEST_BASE_URL` env var > suite YAML value.

## CI Integration

AgentTest works in any CI system. A GitHub Actions workflow is included:

```yaml
- name: Run agent tests
  run: |
    agenttest run tests/suite.yaml \
      --junit-out report.xml \
      --base-url ${{ secrets.AGENT_URL }}
```

Exit codes: `0` = all passed, `2` = test failures, `1` = config error.

See [`.github/workflows/ci.yml`](.github/workflows/ci.yml) for a complete example with matrix testing across Python 3.12 and 3.13.

## Development

```bash
git clone https://github.com/Ameen93/agenttest.git
cd agenttest
uv sync --dev
uv run pytest -q
```

Run the full local CI (unit tests + smoke suite against a mock endpoint):

```bash
make ci
```

## Architecture

```
YAML suite → spec.load_suite() → Runner → HTTPAdapter.call() → evaluate_assertion() → report
```

The adapter layer is extensible — new transport types (subprocess, SDK, etc.) plug in via `adapters.build_adapter()`.

## Roadmap

- Subprocess and SDK adapters
- LLM-as-judge assertion type
- Multi-turn conversation testing
- Variant compare mode (model/prompt matrices)

## License

[MIT](LICENSE)
