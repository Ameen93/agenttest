---
project: agenttest
type: decisions
status: active
stack: python, pyyaml, requests, anthropic, hatchling, pytest
domain: dev-tool, ai-testing
last_analyzed: 2026-03-14
tags: agenttest, dev-tool, ai-testing, python, cli
---

# Decision Log

> Architectural and product decisions inferred from the codebase.

## Tech Stack Choices

**Python 3.12+** — Natural choice for an AI/developer tooling ecosystem. The 3.12 minimum allows modern syntax (`X | Y` unions, `from __future__ import annotations`). Fits the PyPI distribution model well.

**PyYAML for suite definition** — YAML is human-friendly for writing test definitions. Developers already familiar with YAML from CI configs, Docker Compose, etc. Avoids inventing a DSL.

**requests for HTTP** — Simple, synchronous HTTP library. No need for async since tests run sequentially. Well-understood in the Python ecosystem.

**argparse for CLI** — Standard library, zero dependencies. Adequate for the 3-subcommand interface. No need for click/typer overhead.

**hatchling for build** — Modern Python build backend. Pairs well with uv for dependency management.

**anthropic as optional dependency** — Smart split: core tool has zero heavy dependencies (just PyYAML + requests). LLM-judge is opt-in via `agenttest[llm-judge]`.

## Notable Implementation Choices

**Black-box testing philosophy** — The core design decision. Testing agents over HTTP without SDK instrumentation means the tool is language/framework agnostic. Trade-off: no access to internal state, token usage must come from response headers.

**Lazy import for anthropic** — `import anthropic` happens inside `_evaluate_llm_judge()` at assertion evaluation time, not at module import. This means the optional dependency truly doesn't need to be installed unless you use `llm_judge`.

**Dataclass-heavy domain model** — All domain objects (Suite, CaseSpec, TurnSpec, AdapterConfig, AdapterResponse, TestResult, RunOptions) are dataclasses. Enables easy serialization via `dataclasses.asdict()` and clear type contracts.

**Factory pattern for adapters** — `build_adapter(config)` returns the right adapter by type string. Currently only "http" exists, but the pattern is in place for subprocess/SDK adapters.

**Pure functions for streaming parsers** — `parse_sse()`, `parse_ndjson()`, `parse_ai_sdk_ui()` are stateless functions in a dict. Easy to test, easy to add new formats.

**Snapshot normalization** — Responses are normalized before comparison (status_code, json, text) to avoid false diffs from header changes or formatting.

**Two-pass JSON parsing in adapter** — First tries `json.loads(logical_text)`, then falls back to `response.json()`. Handles edge cases where the response text is valid JSON but the content-type isn't set.

**N/M flaky threshold** — Unlike simple reruns (stop at first pass), flaky threshold always runs all M attempts and requires N passes. Better statistical confidence for non-deterministic agents.

## Open Questions

- **PyPI/GitHub status** — resolved 2026-09-28: the PyPI name `agenttest` belongs to an unrelated project, so the PyPI badges and `pip install agenttest` instructions were removed in favour of installing from git. Decide whether to rename the package if PyPI distribution is wanted.
- **Roadmap priorities** — Subprocess adapter, SDK adapter, and variant compare mode are listed. No indication of which is next or timeline.
- **Report history** — `report --last` only shows the most recent run. No way to query, compare, or trend across historical reports (though they're saved as timestamped JSON).
- **Streaming + JSON assertions** — Streaming mode sets `body_json` to None. Should JSON path assertions work on parsed streaming content? Current behavior silently fails.
