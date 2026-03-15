---
project: agenttest
type: features
status: active
stack: python, pyyaml, requests, anthropic, hatchling, pytest
domain: dev-tool, ai-testing
last_analyzed: 2026-03-14
tags: agenttest, dev-tool, ai-testing, python, cli
---

# Features & Capabilities

## Implemented Features

- **YAML test suite definition** — Define test suites declaratively with adapter config, test cases, inputs, and assertions
- **CLI with 3 subcommands** — `init` (scaffold suite), `run` (execute), `report --last` (show previous results)
- **8 assertion types**:
  - `status_code` — HTTP status code equality
  - `contains` — Substring match in response body (or at JSON path)
  - `not_contains` — Substring absence check
  - `regex` — Regex match on response body (or at JSON path)
  - `json_path_equals` — Dotted-path JSON value equality (supports list indexes)
  - `max_latency_ms` — Response time ceiling
  - `min_latency_ms` — Response time floor (detect skipped tool use)
  - `llm_judge` — LLM-based semantic evaluation via Anthropic Claude (configurable model, threshold)
- **Streaming response support** — Parses SSE, NDJSON, and Vercel AI SDK UI formats into logical text before assertion
- **Multi-turn conversation testing** — Stateful conversation flows with accumulated message history per turn
- **Flaky test threshold** — `N/M` format (pass if N of M attempts succeed), always runs all attempts
- **Test reruns** — Retry failing tests N additional times, stop at first pass
- **Snapshot regression testing** — Baseline comparison with unified diff, strict mode for CI
- **Tag filtering** — Run subset of tests by tag (OR logic)
- **Tag-based ordering** — Prioritize test execution by tag (e.g., smoke first, then safety)
- **Fail-fast mode** — Stop on first test failure
- **URL override** — Override adapter URL via `--base-url` flag or `AGENTTEST_BASE_URL` env var
- **Token usage tracking** — Reads `x-usage-input-tokens`/`x-usage-output-tokens` from response headers, aggregates in report
- **JSON report output** — Timestamped JSON reports in `.agenttest/reports/`, with `last_run.json`
- **JUnit XML output** — Standard JUnit XML for GitHub Actions, Jenkins, etc.
- **CI integration** — GitHub Actions workflow with Python 3.12/3.13 matrix, mock server smoke tests
- **Mock agent server** — Included for local testing and CI smoke suites

## Partial / In Progress

None identified — all features appear complete and tested.

## Planned / TODO

From README roadmap:
- **Subprocess adapter** — Test agents via subprocess invocation instead of HTTP
- **SDK adapter** — Test agents via SDK calls
- **Variant compare mode** — Compare responses across model/prompt matrices

## Known Issues

- No TODO, FIXME, or HACK comments found in the codebase
- `report` subcommand only supports `--last` — no ability to query or compare historical reports
- Response body is truncated to 2000 chars in reports (`runner.py:102`) — could lose detail for verbose agents
- Streaming mode disables JSON parsing of the response body (`adapters.py:48`) — assertions requiring `body_json` won't work in streaming mode
