---
project: agenttest
type: overview
status: active
stack: python, pyyaml, requests, anthropic, hatchling, pytest
domain: dev-tool, ai-testing
last_analyzed: 2026-03-14
tags: agenttest, dev-tool, ai-testing, python, cli, yaml
---

# AgentTest
> pytest-style CLI for testing AI agent HTTP endpoints using YAML-defined test suites.

## What This Is

AgentTest is a developer tool that lets you write repeatable test suites for AI agent endpoints in YAML and run them from the command line. It takes the philosophy of "test from the outside" — no SDK instrumentation required. You point it at an HTTP endpoint, define your assertions, and get deterministic pass/fail results.

The tool supports eight assertion types ranging from simple (status code, substring) to semantic (LLM-as-judge via Anthropic's API). It handles the non-deterministic nature of AI responses through flaky thresholds, reruns, and snapshot regression tracking. Output formats include JSON and JUnit XML, making it CI-ready out of the box.

It is an open-source Python package under the MIT license with GitHub Actions CI running against Python 3.12 and 3.13. The repository is set up for PyPI distribution via `pyproject.toml`.

## Problem It Solves

Most AI evaluation tools require you to instrument your agent's code with an SDK to test it. AgentTest tests agents as black boxes over HTTP — exactly how they run in production. This means you can test any agent regardless of language, framework, or hosting, and you can commit test suites alongside your code and run them in CI.

## Target User

Developers building AI agents who want to add automated testing to their CI/CD pipeline. Particularly useful for teams that need regression testing on agent behavior, safety/policy compliance checks, or contract testing on agent response shapes.

## Current Status

**Active / Alpha-stage CLI tool (v0.1.0)**

Evidence:
- Public GitHub repo with CI badges (`github.com/Ameen93/agenttest`)
- Comprehensive README with install, quickstart, and feature docs
- CHANGELOG following Keep a Changelog format
- CONTRIBUTING.md with clear contributor workflow
- MIT license
- Zero TODO/FIXME comments in source code
- Test suite covering the main modules and CLI paths
- Clean, well-factored codebase

This status is based on repository evidence only; no external release status is asserted here.

## Key Links & Entry Points

| Item | Location |
|------|----------|
| CLI entry point | `src/agenttest/cli.py:main()` |
| Package script | `agenttest` → `agenttest.cli:main` (pyproject.toml) |
| Install command | `pip install agenttest` |
| GitHub | `github.com/Ameen93/agenttest` |
| CI | `.github/workflows/ci.yml` |
| Example suites | `examples/basic.suite.yaml`, `examples/ci.suite.yaml` |
| Mock server (testing) | `scripts/mock_agent_server.py` |
| Local CI script | `scripts/run_local_ci.sh` |
| Report storage | `.agenttest/reports/` |
| Snapshot storage | `.agenttest/snapshots/` |
