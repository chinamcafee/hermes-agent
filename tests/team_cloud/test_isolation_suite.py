from __future__ import annotations

import json
import os
from pathlib import Path


ISOLATION_SCRIPT = Path("scripts/team-cloud-isolation-smoke.sh")
ISOLATION_MATRIX = Path("teamDoc/GADoc/artifacts/p2-isolation-suite-v0.json")


def test_isolation_smoke_script_invokes_identity_memory_and_cloud_paths():
    content = ISOLATION_SCRIPT.read_text(encoding="utf-8")

    assert os.access(ISOLATION_SCRIPT, os.X_OK)
    assert "tests/team_cloud/test_memory_query_layer.py" in content
    assert "tests/team_cloud/test_memory_prefetch_pipeline.py" in content
    assert "tests/team_cloud/test_team_memory_provider.py" in content
    assert "tests/team_cloud/test_external_identity_resolver.py" in content
    assert "tests/gateway/test_gateway_team_identity_resolver.py" in content
    assert "tests/gateway/test_api_server_team_headers.py" in content
    assert "tests/team_cloud/test_cloud_session_history.py" in content
    assert "tests/team_cloud/test_runtime_event_bridge.py" in content


def test_isolation_acceptance_matrix_documents_required_boundaries():
    matrix = json.loads(ISOLATION_MATRIX.read_text(encoding="utf-8"))
    domains = {check["domain"] for check in matrix["checks"]}

    assert matrix["schema_version"] == 1
    assert matrix["name"] == "p2-memory-runtime-isolation-suite"
    assert {
        "personal_memory_isolation",
        "team_memory_authz_isolation",
        "gateway_team_identity_session_prefix",
        "api_server_trusted_identity_headers",
        "cloud_history_org_project_member_filter",
        "runtime_event_bridge_session_binding",
    } <= domains
    assert all(check["command"].startswith("scripts/run_tests.sh ") for check in matrix["checks"])
