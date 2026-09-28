# AgentTest

**pytest for AI agent endpoints.** Define test suites in YAML, run them against any HTTP endpoint, get deterministic pass/fail results with snapshot regression tracking.

[![CI](https://github.com/Ameen93/agenttest/actions/workflows/ci.yml/badge.svg)](https://github.com/Ameen93/agenttest/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

Most AI evaluation tools require SDK instrumentation — you modify your agent's code to test it. AgentTest takes a different approach: **test from the outside, over HTTP, exactly as your agent runs in production.** Write YAML, commit it alongside your code, run it in CI.

## Install

Not on PyPI: the name `agenttest` is already taken there by an unrelated
project, so install from source.

```bash
pip install git+https://github.com/Ameen93/agenttest
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv pip install git+https://github.com/Ameen93/agenttest
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

Eight assertion types cover the deterministic and semantic layers of agent testing:

| Type | What it checks | Example |
|---|---|---|
| `status_code` | HTTP status code | `equals: 200` |
| `contains` | Substring in response body | `value: "hello"` |
| `not_contains` | Substring absent from response | `value: "traceback"` |
| `regex` | Regex match on response body | `pattern: "(?i)safe\|policy"` |
| `json_path_equals` | Dotted-path JSON value | `path: meta.intent`, `equals: "answer"` |
| `max_latency_ms` | Response time ceiling | `le: 3000` |
| `min_latency_ms` | Response time floor (detect skipped tool use) | `ge: 1000` |
| `llm_judge` | LLM-based semantic evaluation | `criteria: "Is the response helpful?"` |

### LLM-as-Judge

For semantic quality checks that go beyond keyword matching:

```yaml
assertions:
  - type: llm_judge
    criteria: "Did the assistant provide helpful, accurate advice?"
    pass_threshold: 0.8   # score 0.0–1.0, default 0.8
    model: claude-haiku-4-5-20251001  # optional, default haiku
```

Requires the optional `anthropic` dependency:

```bash
pip install "agenttest[llm-judge] @ git+https://github.com/Ameen93/agenttest"
```

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

## Streaming Responses

Test streaming endpoints (SSE, NDJSON, Vercel AI SDK) by setting `stream_mode` on the adapter. AgentTest buffers the stream and parses it into logical text before running assertions:

```yaml
adapter:
  type: http
  url: http://localhost:3000/api/chat
  method: POST
  stream_mode: ai-sdk-ui   # also: sse, ndjson
```

Supported modes:
- **`sse`** — Server-Sent Events (`data:` lines)
- **`ndjson`** — Newline-delimited JSON (extracts `text`/`content`/`delta.content`)
- **`ai-sdk-ui`** — Vercel AI SDK format (`0:"text"` lines)

## Multi-Turn Conversations

Test stateful conversation flows where each turn uses the AI's actual previous responses:

```yaml
- id: qualification_flow
  type: conversation
  turns:
    - user: "I want a Toyota Hilux"
      assertions:
        - type: contains
          value: "budget"
    - user: "Around R600k"
      assertions:
        - type: regex
          pattern: "(?i)dealer"
```

Each turn sends the accumulated message history to the endpoint as `{"messages": [...]}`.

## Reruns

Retry failing tests to handle flaky agent responses:

```bash
agenttest run suite.yaml --reruns 2
```

## Flaky Threshold

For non-deterministic AI responses, require N passes out of M attempts:

```yaml
- id: creative_test
  flaky_threshold: 2/3  # pass if 2 out of 3 attempts pass
  input: { message: "Write a poem" }
  assertions:
    - type: contains
      value: "rhyme"
```

Unlike `--reruns` (which stops at first pass), flaky threshold always runs all M attempts.

## Tag Ordering & Fail-Fast

Control test execution order by tag priority and stop on first failure:

```bash
# Run smoke tests first, then safety, then the rest
agenttest run suite.yaml --tags-order smoke,safety --fail-fast
```

## Cost Tracking

If your agent returns token usage in response headers (`x-usage-input-tokens`, `x-usage-output-tokens`), AgentTest tracks and reports them:

```
Summary: total=5 passed=5 failed=0 duration=1234.5ms
Tokens: input=2500 output=1800
```

Token counts are also included in the JSON report under `summary.input_tokens` and `summary.output_tokens`.

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

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup instructions and development workflow.

## Development

```bash
git clone https://github.com/Ameen93/agenttest.git
cd agenttest
uv sync --dev
uv run pytest -q
```

Available `make` targets:

```bash
make sync     # Install/sync dependencies
make test     # Run unit tests
make smoke    # Mock server + CLI smoke suite
make ci       # Full local CI (sync + test + smoke)
```

## Architecture

```
YAML suite → spec.load_suite() → Runner → HTTPAdapter.call() → evaluate_assertion() → report
```

The adapter layer is extensible — new transport types (subprocess, SDK, etc.) plug in via `adapters.build_adapter()`.

## Roadmap

- Subprocess and SDK adapters
- Variant compare mode (model/prompt matrices)

See [CHANGELOG.md](CHANGELOG.md) for release history.

## License

[MIT](LICENSE)
