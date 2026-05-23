from __future__ import annotations

import json
import os
from pathlib import Path


ARTIFACT = Path("teamDoc/GADoc/artifacts/load/team-cloud-load-test-plan-v0.json")
DOC = Path("teamDoc/GADoc/P4-07-load-test-scripts.md")
SCRIPT = Path("scripts/team-cloud-load-test-plan.py")
SMOKE_SCRIPT = Path("scripts/team-cloud-foundation-smoke.sh")
SMOKE_MATRIX = Path("teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json")

REQUIRED_SCENARIOS = {
    "concurrent_chat_runs",
    "memory_prefetch",
    "spicedb_batch_check",
    "embedding_import",
    "personal_backup",
    "org_export",
    "gateway_group_session",
}


def test_load_test_plan_builder_covers_beta_scenarios_and_thresholds():
    from team_cloud.load_testing import build_load_test_plan

    plan = build_load_test_plan()
    scenarios = {scenario["id"]: scenario for scenario in plan["scenarios"]}

    assert plan["schema_version"] == 1
    assert plan["name"] == "team-cloud-load-test-plan-v0"
    assert set(scenarios) == REQUIRED_SCENARIOS
    assert scenarios["concurrent_chat_runs"]["concurrency"] >= 25
    assert scenarios["concurrent_chat_runs"]["target_p95_ms"] <= 2500
    assert scenarios["memory_prefetch"]["target_p95_ms"] <= 500
    assert scenarios["spicedb_batch_check"]["target_p95_ms"] <= 250
    assert scenarios["personal_backup"]["success_criteria"]["error_rate"] == 0
    assert all(scenario["duration_seconds"] >= 300 for scenario in plan["scenarios"])
    assert all(scenario["telemetry"] for scenario in plan["scenarios"])


def test_load_test_plan_artifact_script_docs_and_smoke_are_registered():
    from team_cloud.load_testing import build_load_test_plan

    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    doc = DOC.read_text(encoding="utf-8")
    script = SCRIPT.read_text(encoding="utf-8")
    smoke = SMOKE_SCRIPT.read_text(encoding="utf-8")
    matrix = json.loads(SMOKE_MATRIX.read_text(encoding="utf-8"))
    domains = {entry["domain"] for entry in matrix["checks"]}

    assert artifact == build_load_test_plan()
    assert os.access(SCRIPT, os.X_OK)
    assert "team-cloud-load-test-plan-v0.json" in script
    assert "concurrent_chat_runs" in doc
    assert "memory_prefetch" in doc
    assert "spicedb_batch_check" in doc
    assert "tests/team_cloud/test_load_test_scripts.py" in smoke
    assert "load_test_scripts" in domains
