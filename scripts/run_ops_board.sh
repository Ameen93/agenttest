#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "AgentTest Ops Board running at http://127.0.0.1:8787"
echo "Login with AGENTTEST_OPS_USER / AGENTTEST_OPS_PASS (defaults: ameen/changeme)"
python ops/server.py
