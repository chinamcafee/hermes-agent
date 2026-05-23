from __future__ import annotations

import json
import os
from pathlib import Path


ARTIFACT = Path("teamDoc/GADoc/artifacts/release/team-cloud-support-playbook-v0.json")
DOC = Path("teamDoc/GADoc/P5-09-support-playbook.md")
SCRIPT = Path("scripts/team-cloud-support-playbook.py")
SMOKE_SCRIPT = Path("scripts/team-cloud-foundation-smoke.sh")
SMOKE_MATRIX = Path("teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json")


def test_support_playbook_covers_response_slas_diagnostics_logs_and_escalation():
    from team_cloud.support_playbook import build_support_playbook_package

    package = build_support_playbook_package()
    tiers = {tier["severity"]: tier for tier in package["support_tiers"]}
    diagnostics = {command["id"] for command in package["diagnostic_commands"]}
    logs = {item["id"] for item in package["log_collection"]}
    escalations = {path["id"] for path in package["escalation_paths"]}

    assert package["schema_version"] == 1
    assert package["name"] == "team-cloud-support-playbook-v0"
    assert tiers["P0"]["first_response_minutes"] == 15
    assert tiers["P1"]["first_response_minutes"] == 60
    assert {"foundation_smoke", "collect_hermes_logs", "runbook_summary"} <= diagnostics
    assert {"agent_log", "errors_log", "gateway_log", "team_api_logs", "audit_export"} <= logs
    assert {"security", "sre", "release"} <= escalations
    assert package["upgrade_path"] == "P5-06 runbook_summary -> P4-09 upgrade_rollback"


def test_support_playbook_artifact_script_docs_and_smoke_are_registered():
    from team_cloud.support_playbook import build_support_playbook_package

    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    doc = DOC.read_text(encoding="utf-8")
    script = SCRIPT.read_text(encoding="utf-8")
    smoke = SMOKE_SCRIPT.read_text(encoding="utf-8")
    matrix = json.loads(SMOKE_MATRIX.read_text(encoding="utf-8"))
    domains = {entry["domain"] for entry in matrix["checks"]}

    assert artifact == build_support_playbook_package()
    assert os.access(SCRIPT, os.X_OK)
    assert "team-cloud-support-playbook-v0.json" in script
    assert "first_response_minutes" in doc
    assert "diagnostic_commands" in doc
    assert "log_collection" in doc
    assert "upgrade_path" in doc
    assert "tests/team_cloud/test_support_playbook.py" in smoke
    assert "support_playbook" in domains
