---
project: agenttest
type: architecture
status: active
stack: python, pyyaml, requests, anthropic, hatchling, pytest
domain: dev-tool, ai-testing
last_analyzed: 2026-03-14
tags: agenttest, dev-tool, ai-testing, python, cli
---

# Architecture

## Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Language | Python 3.12+ | Core runtime |
| CLI | argparse | Command-line interface |
| Suite format | YAML (PyYAML) | Test suite definition |
| HTTP transport | requests | Agent endpoint communication |
| LLM judge | anthropic (optional) | Semantic evaluation via Claude |
| Build system | hatchling | Package building |
| Package manager | uv | Dependency management |
| Testing | pytest | Unit tests |
| CI | GitHub Actions | Automated testing (Python 3.12, 3.13 matrix) |

## System Diagram

```
                    YAML Suite File
                         │
                         ▼
                 ┌───────────────┐
                 │   spec.py     │  Parse YAML → Suite/CaseSpec/TurnSpec dataclasses
                 │ load_suite()  │
                 └───────┬───────┘
                         │
                         ▼
                 ┌───────────────┐
                 │   cli.py      │  argparse CLI: init / run / report
                 │   main()      │  URL override logic (flag > env > YAML)
                 └───────┬───────┘
                         │
                         ▼
                 ┌───────────────┐
                 │  runner.py    │  Test execution engine
                 │  Runner.run() │  Tag filtering, ordering, reruns, flaky, fail-fast
                 └───────┬───────┘
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
        ┌──────────┐ ┌──────────┐ ┌──────────────┐
        │ Standard │ │  Flaky   │ │ Conversation │
        │ _run_std │ │_run_flaky│ │ _exec_conv   │
        └────┬─────┘ └────┬─────┘ └──────┬───────┘
             │             │              │
             └──────┬──────┘──────────────┘
                    ▼
            ┌───────────────┐
            │ adapters.py   │  HTTPAdapter.call() → AdapterResponse
            │ build_adapter │  (extensible: new adapters plug in here)
            └───────┬───────┘
                    │
                    ▼ (if stream_mode set)
            ┌───────────────┐
            │ streaming.py  │  parse_sse / parse_ndjson / parse_ai_sdk_ui
            └───────┬───────┘
                    │
                    ▼
            ┌───────────────┐
            │assertions.py  │  evaluate_assertion() → (bool, detail_str)
            │               │  8 types incl. llm_judge (lazy anthropic import)
            └───────┬───────┘
                    │
              ┌─────┼─────┐
              ▼           ▼
      ┌────────────┐ ┌──────────────┐
      │snapshots.py│ │ reporting.py │
      │ compare /  │ │ JSON + JUnit │
      │ save / load│ │ XML output   │
      └────────────┘ └──────────────┘
```

## Key Components

### spec.py — Suite Parser
- **Location**: `src/agenttest/spec.py`
- **Responsibility**: Parse YAML files into typed dataclasses
- **Key types**: `Suite`, `CaseSpec`, `TurnSpec`, `AdapterConfig`
- **Entry point**: `load_suite(path)` — validates required fields, stream modes, flaky thresholds
- **Notable**: Validates eagerly at parse time (flaky threshold format, stream mode names, required fields)

### adapters.py — Transport Layer
- **Location**: `src/agenttest/adapters.py`
- **Responsibility**: Send HTTP requests to agent endpoints, return structured responses
- **Key types**: `HTTPAdapter`, `AdapterResponse`
- **Entry point**: `build_adapter(config)` — factory function for adapter creation
- **Notable**: Extensible by design — new adapter types (subprocess, SDK) plug in via `build_adapter()`. Handles stream mode by delegating to streaming parsers.

### assertions.py — Assertion Engine
- **Location**: `src/agenttest/assertions.py`
- **Responsibility**: Evaluate assertions against response data
- **Entry point**: `evaluate_assertion(assertion_dict, *, status_code, body_text, body_json, latency_ms)`
- **Returns**: `(bool, str)` tuple — pass/fail + human-readable detail
- **Notable**: `llm_judge` uses lazy `import anthropic` so the dependency is optional. `get_path()` supports dotted JSON paths with list index support.

### streaming.py — Stream Parsers
- **Location**: `src/agenttest/streaming.py`
- **Responsibility**: Parse streaming response formats into logical text
- **Functions**: `parse_sse()`, `parse_ndjson()`, `parse_ai_sdk_ui()`
- **Notable**: Pure functions, no state. `PARSERS` dict maps mode names to functions. Handles SSE `[DONE]` sentinel, NDJSON delta/content fields, Vercel AI SDK `0:"text"` format.

### runner.py — Execution Engine
- **Location**: `src/agenttest/runner.py`
- **Responsibility**: Orchestrate test execution with all runtime features
- **Key types**: `Runner`, `RunOptions`, `TestResult`
- **Features**: Tag filtering/ordering, reruns, flaky thresholds (N/M), multi-turn conversations, fail-fast, snapshot comparison, token tracking
- **Notable**: Three execution paths — `_run_standard`, `_run_flaky`, `_execute_conversation`. Conversations accumulate message history across turns.

### snapshots.py — Snapshot Regression
- **Location**: `src/agenttest/snapshots.py`
- **Responsibility**: Store and compare response baselines
- **Storage**: `.agenttest/snapshots/<suite>/<test_id>.json`
- **Notable**: Normalizes responses before comparison. Produces unified diff with truncation for large changes. Supports strict mode (fail on change) vs. auto-update mode.

### reporting.py — Report Output
- **Location**: `src/agenttest/reporting.py`
- **Responsibility**: Write test results to JSON and JUnit XML formats
- **Storage**: `.agenttest/reports/run-<timestamp>.json` + `last_run.json`
- **Notable**: JUnit XML uses standard `<testsuite>/<testcase>/<failure>` structure for CI tool compatibility.

### cli.py — CLI Interface
- **Location**: `src/agenttest/cli.py`
- **Responsibility**: Parse CLI args and dispatch to commands
- **Commands**: `init` (scaffold suite), `run` (execute suite), `report --last` (show last results)
- **Notable**: URL override priority: `--base-url` flag > `AGENTTEST_BASE_URL` env var > suite YAML value. Exit codes: 0=pass, 1=config error, 2=test failures.

## Data Model

No database. Data is YAML in, JSON out:

- **Input**: YAML suite files defining adapter config + test cases with assertions
- **State**: `.agenttest/` directory with:
  - `snapshots/<suite>/<test_id>.json` — normalized response baselines
  - `reports/run-<timestamp>.json` — timestamped run results
  - `reports/last_run.json` — symlink/copy of most recent run

## External Dependencies

| Dependency | Role | Required? |
|-----------|------|-----------|
| PyYAML | Parse YAML suite files | Yes |
| requests | HTTP transport to agent endpoints | Yes |
| anthropic | LLM-as-judge assertion type | Optional (`agenttest[llm-judge]`) |

## Notable Patterns

- **Factory pattern** in `build_adapter()` — allows plugging in new transport types without changing runner
- **Lazy imports** for optional `anthropic` dependency — only loaded when `llm_judge` assertion is used
- **Strategy pattern** in runner — three execution strategies (standard, flaky, conversation) selected by test spec
- **Pure parser functions** in streaming.py — stateless, easily testable
- **Early validation** in spec.py — catches config errors at parse time, not runtime
- **Dataclass-heavy design** — all domain objects are dataclasses, serialized via `dataclasses.asdict()`
