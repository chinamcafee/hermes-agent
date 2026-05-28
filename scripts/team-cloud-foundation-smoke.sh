#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

MATRIX="teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json"
if [[ ! -f "$MATRIX" ]]; then
  echo "Missing smoke matrix: $MATRIX" >&2
  exit 2
fi

scripts/run_tests.sh \
  tests/test_project_metadata.py \
  tests/run_agent/test_memory_provider_init.py \
  tests/run_agent/test_team_soul_runtime.py \
  tests/hermes_cli/test_team_cloud_cli.py \
  tests/hermes_cli/test_cloud_backup_cli.py \
  tests/hermes_cli/test_team_soul.py \
  tests/hermes_cli/test_team_tool_policy.py \
  tests/hermes_cli/test_team_memory_provider.py \
  tests/hermes_cli/test_team_memory_provider_tools.py \
  tests/hermes_cli/test_web_server_team_bridge_profiles.py

(cd team_cloud && go test ./...)
(cd team_cloud/dashboard && npm test -- --run)
