#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "[agenttest] syncing dependencies"
uv sync --dev

echo "[agenttest] running unit tests"
uv run pytest -q

echo "[agenttest] starting mock endpoint"
uv run python scripts/mock_agent_server.py >/tmp/agenttest-mock.log 2>&1 &
MOCK_PID=$!
cleanup() {
  kill "$MOCK_PID" >/dev/null 2>&1 || true
}
trap cleanup EXIT
sleep 1

echo "[agenttest] running CLI smoke suite"
mkdir -p artifacts
uv run agenttest run examples/ci.suite.yaml \
  --json-out artifacts/agenttest-report.json \
  --junit-out artifacts/agenttest-report.xml

echo "[agenttest] local CI complete"
