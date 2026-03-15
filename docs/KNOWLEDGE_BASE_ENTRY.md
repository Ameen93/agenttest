---
project: agenttest
type: kb-entry
status: active
stack: python, pyyaml, requests, anthropic, hatchling, pytest
domain: dev-tool, ai-testing
last_analyzed: 2026-03-14
tags: agenttest, dev-tool, ai-testing, python, cli, open-source
---

# Knowledge Base Entry — AgentTest

> Canonical single-file reference for cross-project knowledge base.

## Tags

dev-tool, ai-testing, python, cli, yaml, open-source, pypi, http-testing, llm-evaluation, active

## Summary

AgentTest is a Python CLI tool (MIT license) for testing AI agent HTTP endpoints. You define test suites in YAML with assertions (status code, substring, regex, JSON path, latency, LLM-as-judge) and run them from the command line or CI. It handles non-deterministic AI responses through flaky thresholds and reruns, tracks output drift via snapshot regression, and supports streaming responses (SSE, NDJSON, Vercel AI SDK) and multi-turn conversations. The codebase is small, well-tested, and focused at v0.1.0. Repository roadmap items include subprocess/SDK adapters and variant compare.

## Relationships to Other Projects

- **ameen-portfolio-site** — AgentTest is showcased on the portfolio site
- **carsearch** — Contains an `agenttest.suite.yaml` file, indicating it uses AgentTest for testing
- **sebenza** — Contains an `agenttest.suite.yaml` file, indicating it uses AgentTest for testing
- Potentially useful for testing any AI agent built in other projects (fynkos, momsmykonos, etc.)

## Reusable Patterns

- **YAML-to-dataclass parsing pattern** — `spec.py` demonstrates a clean pattern for parsing config files into validated, typed dataclasses with early error detection. Reusable for any config-driven CLI tool.
- **Factory + lazy import pattern** — `build_adapter()` + lazy `import anthropic` shows how to keep optional dependencies truly optional while maintaining extensibility.
- **Pure stream parser pattern** — Stateless parser functions in a dict (`PARSERS`) is a clean approach for format-specific parsing without class overhead.
- **Snapshot regression pattern** — Normalize → compare → unified diff is a general-purpose approach reusable for any response regression testing.
- **CLI project structure** — `src/` layout, `pyproject.toml` with `[project.scripts]`, hatchling build, uv for deps, Makefile for common tasks, GitHub Actions CI — good template for any Python CLI tool.

## Lessons & Insights

- **Keep core dependencies minimal** — Only PyYAML + requests as required deps. Optional extras for heavy features (anthropic). Makes installation fast and adoption easy.
- **Test the testing tool** — The project uses its own mock server to smoke-test itself end-to-end. Running `make smoke` starts a mock agent, runs agenttest against it, and checks the output. Good CI practice.
- **Early validation catches bugs** — Validating flaky thresholds, stream modes, and required fields at YAML parse time (not runtime) means errors surface immediately, not mid-test-run.
- **Focused scope helps quality** — The repository stays small and readable while still covering the main runner, parser, CLI, and streaming paths with tests.
