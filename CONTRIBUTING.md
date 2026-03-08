# Contributing to AgentTest

## Setup

```bash
git clone https://github.com/Ameen93/agenttest.git
cd agenttest
uv sync --dev
```

## Running tests

```bash
# Unit tests
uv run pytest -q

# Single test
uv run pytest tests/test_assertions.py::test_contains

# Full local CI (unit tests + smoke suite against mock endpoint)
make ci
```

## Makefile targets

| Target | What it does |
|--------|-------------|
| `make sync` | Install/sync dependencies |
| `make test` | Run unit tests |
| `make smoke` | Start mock server, run CLI smoke suite |
| `make ci` | Full local CI (sync + test + smoke) |

## Project structure

```
src/agenttest/
  spec.py        # YAML parsing into dataclasses
  adapters.py    # HTTP transport layer
  assertions.py  # Assertion evaluation
  streaming.py   # SSE/NDJSON/AI-SDK stream parsers
  runner.py      # Test execution engine
  snapshots.py   # Baseline snapshot storage
  reporting.py   # JSON/JUnit report writers
  cli.py         # CLI entry point
```

## Adding a new assertion type

1. Add the evaluation logic to `assertions.py` in `evaluate_assertion()`
2. Add test cases in `tests/test_assertions.py`
3. Document the assertion in `README.md` in the Assertions table

## Adding a new adapter type

1. Create the adapter class in `adapters.py` returning `AdapterResponse`
2. Register it in `build_adapter()`
3. Add any new config fields to `AdapterConfig` in `spec.py`

## Submitting changes

1. Fork the repository
2. Create a feature branch
3. Make sure `make ci` passes
4. Open a pull request against `master`
