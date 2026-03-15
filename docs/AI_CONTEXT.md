---
project: agenttest
type: ai-context
status: active
stack: python, pyyaml, requests, anthropic, hatchling, pytest
domain: dev-tool, ai-testing
last_analyzed: 2026-03-14
tags: agenttest, dev-tool, ai-testing, python, cli
---

# AI Context File — AgentTest

> This file is optimized for loading into an AI assistant to provide full project context.

## Project Identity
- **Name**: AgentTest
- **Domain**: Developer tooling / AI agent testing
- **Status**: Active, published (v0.1.0)
- **Stack**: Python 3.12+, PyYAML, requests, optional anthropic
- **Location**: `/home/ameen/projects/agenttest/`

## One-Paragraph Summary

AgentTest is a Python CLI tool (MIT-licensed and packaged via `pyproject.toml`) that tests AI agent HTTP endpoints from the outside using YAML-defined test suites. The pipeline is: YAML suite → `spec.load_suite()` → `Runner` → `HTTPAdapter.call()` → `evaluate_assertion()` → JSON/JUnit report. It supports 8 assertion types (including LLM-as-judge via Anthropic), streaming response parsing (SSE, NDJSON, Vercel AI SDK), multi-turn conversation testing, flaky thresholds (N/M), snapshot regression, tag filtering/ordering, fail-fast, reruns, token tracking, and URL override.

## Key Concepts & Terminology

- **Suite** — A YAML file defining an adapter config and a list of test cases
- **Adapter** — Transport layer (currently only HTTP). Factory pattern via `build_adapter()`
- **CaseSpec** — A single test case with id, input payload, assertions, and optional tags/flaky threshold
- **TurnSpec** — A single turn in a multi-turn conversation test
- **Assertion** — A check against the response (8 types: status_code, contains, not_contains, regex, json_path_equals, max_latency_ms, min_latency_ms, llm_judge)
- **Flaky threshold** — Format `N/M` meaning "pass if N out of M attempts pass"
- **Snapshot** — Normalized baseline response stored in `.agenttest/snapshots/` for regression detection
- **Stream mode** — Parsing mode for streaming responses: `sse`, `ndjson`, `ai-sdk-ui`
- **LLM judge** — Assertion that sends the response to Claude for semantic evaluation with a score 0.0-1.0

## Architecture in Brief

Single Python package with 8 modules. Data flows linearly: YAML → parsed dataclasses → Runner orchestrates execution → HTTPAdapter sends requests → streaming parsers normalize response → assertions evaluate → snapshots compare baselines → reporters write JSON/JUnit. The adapter layer is designed to be extensible for future subprocess/SDK adapters.

## Current Sprint / Focus

The tool is functionally broad for v0.1.0. Roadmap items called out in the repository are subprocess/SDK adapters and variant compare mode.

## Important Constraints

- Only HTTP adapter exists — agents must be reachable over HTTP
- `llm_judge` requires the optional `anthropic` package and a valid `ANTHROPIC_API_KEY`
- Streaming mode disables JSON body parsing — JSON-dependent assertions won't work with streaming
- Response bodies are truncated to 2000 chars in reports
- Python 3.12+ required (uses `X | Y` union syntax)

## File Map (Key Files Only)

| Path | Purpose |
|------|---------|
| `src/agenttest/cli.py` | CLI entry point — init/run/report commands |
| `src/agenttest/spec.py` | YAML parser → Suite/CaseSpec/AdapterConfig dataclasses |
| `src/agenttest/runner.py` | Test execution engine (standard/flaky/conversation) |
| `src/agenttest/adapters.py` | HTTPAdapter — sends requests, returns AdapterResponse |
| `src/agenttest/assertions.py` | 8 assertion types including llm_judge |
| `src/agenttest/streaming.py` | SSE/NDJSON/AI-SDK-UI stream parsers |
| `src/agenttest/snapshots.py` | Baseline snapshot storage and comparison |
| `src/agenttest/reporting.py` | JSON and JUnit XML report writers |
| `pyproject.toml` | Package metadata, deps, CLI script entry |
| `.github/workflows/ci.yml` | GitHub Actions CI (Python 3.12/3.13 matrix) |
| `examples/ci.suite.yaml` | CI smoke test suite |
| `scripts/mock_agent_server.py` | Mock HTTP endpoint for testing |
| `Makefile` | sync/test/smoke/ci targets |
