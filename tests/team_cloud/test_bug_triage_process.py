from __future__ import annotations

import json
import os
from pathlib import Path


ARTIFACT = Path("teamDoc/GADoc/artifacts/pilot/team-cloud-bug-triage-v0.json")
DOC = Path("teamDoc/GADoc/P4-11-bug-triage-process.md")
SCRIPT = Path("scripts/team-cloud-bug-triage.py")
SMOKE_SCRIPT = Path("scripts/team-cloud-foundation-smoke.sh")
SMOKE_MATRIX = Path("teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json")


def test_bug_triage_process_defines_severity_sla_and_blocker_rules():
    from team_cloud.triage import build_bug_triage_process

    process = build_bug_triage_process()
    severities = {item["severity"]: item for item in process["severity_levels"]}

    assert process["schema_version"] == 1
    assert process["name"] == "team-cloud-bug-triage-v0"
    assert {"P0", "P1", "P2", "P3"} == set(severities)
    assert severities["P0"]["first_response_minutes"] <= 30
    assert severities["P1"]["first_response_minutes"] <= 120
    assert "security_data_leak" in process["release_blocker_rules"]
    assert "cross_org_access" in process["release_blocker_rules"]
    assert process["escalation"]["owner"] == "team-cloud-beta-coordinator"


def test_bug_triage_artifact_script_docs_and_smoke_are_registered():
    from team_cloud.triage import build_bug_triage_process

    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    doc = DOC.read_text(encoding="utf-8")
    script = SCRIPT.read_text(encoding="utf-8")
    smoke = SMOKE_SCRIPT.read_text(encoding="utf-8")
    matrix = json.loads(SMOKE_MATRIX.read_text(encoding="utf-8"))
    domains = {entry["domain"] for entry in matrix["checks"]}

    assert artifact == build_bug_triage_process()
    assert os.access(SCRIPT, os.X_OK)
    assert "team-cloud-bug-triage-v0.json" in script
    assert "release_blocker_rules" in doc
    assert "severity_levels" in doc
    assert "tests/team_cloud/test_bug_triage_process.py" in smoke
    assert "bug_triage_process" in domains
