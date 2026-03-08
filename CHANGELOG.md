# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-03-08

### Added

- YAML-based test suite definition with `load_suite()` parser
- HTTP adapter for testing agent endpoints (`adapters.build_adapter()`)
- Eight assertion types: `status_code`, `contains`, `not_contains`, `regex`, `json_path_equals`, `max_latency_ms`, `min_latency_ms`, `llm_judge`
- LLM-as-judge semantic evaluation via optional `anthropic` dependency
- Streaming response support: SSE, NDJSON, Vercel AI SDK (`stream_mode`)
- Multi-turn conversation testing (`type: conversation` with `turns`)
- Flaky test threshold (`flaky_threshold: N/M`)
- Snapshot regression testing with baseline comparison
- Tag filtering (`--tags`) and tag-based execution ordering (`--tags-order`)
- Fail-fast mode (`--fail-fast`)
- Test reruns for non-deterministic responses (`--reruns`)
- Token usage tracking from response headers
- JSON and JUnit XML report output
- URL override via `--base-url` flag and `AGENTTEST_BASE_URL` env var
- CLI with `init`, `run`, and `report` subcommands

[0.1.0]: https://github.com/Ameen93/agenttest/releases/tag/v0.1.0
