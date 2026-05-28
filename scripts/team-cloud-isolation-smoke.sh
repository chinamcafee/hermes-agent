#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

MATRIX="teamDoc/GADoc/artifacts/p2-isolation-suite-v0.json"
if [[ ! -f "$MATRIX" ]]; then
  echo "Missing isolation matrix: $MATRIX" >&2
  exit 2
fi

scripts/run_tests.sh \
  tests/run_agent/test_memory_provider_init.py \
  tests/gateway/test_api_server_team_headers.py \
  tests/gateway/test_gateway_team_identity_resolver.py \
  tests/hermes_cli/test_team_cloud_cli.py \
  tests/hermes_cli/test_team_memory_provider.py \
  tests/hermes_cli/test_team_memory_provider_tools.py

(cd team_cloud && go test ./internal/httpapi -count=1)
