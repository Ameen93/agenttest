.PHONY: sync test smoke ci

sync:
	uv sync --dev

test:
	uv run pytest -q

smoke:
	uv run python scripts/mock_agent_server.py >/tmp/agenttest-mock.log 2>&1 & echo $$! > /tmp/agenttest-mock.pid
	sleep 1
	uv run agenttest run examples/ci.suite.yaml --json-out artifacts/agenttest-report.json --junit-out artifacts/agenttest-report.xml
	-kill "$$(cat /tmp/agenttest-mock.pid)" >/dev/null 2>&1

ci:
	bash scripts/run_local_ci.sh
