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
  tests/team_cloud/test_memory_query_layer.py \
  tests/team_cloud/test_memory_prefetch_pipeline.py \
  tests/team_cloud/test_team_memory_provider.py \
  tests/team_cloud/test_external_identity_resolver.py \
  tests/team_cloud/test_web_chat_entry.py \
  tests/team_cloud/test_cloud_session_history.py \
  tests/team_cloud/test_runtime_event_bridge.py \
  tests/team_cloud/test_platform_security_negative.py
