from __future__ import annotations

import json
import os
from pathlib import Path


ARTIFACT = Path("teamDoc/GADoc/artifacts/chaos/team-cloud-chaos-drills-v0.json")
DOC = Path("teamDoc/GADoc/P4-13-chaos-drills.md")
SCRIPT = Path("scripts/team-cloud-chaos-drills.py")
SMOKE_SCRIPT = Path("scripts/team-cloud-foundation-smoke.sh")
SMOKE_MATRIX = Path("teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json")


def test_chaos_drills_cover_spicedb_minio_postgres_and_recovery_gates():
    from team_cloud.chaos import build_chaos_drill_matrix

    matrix = build_chaos_drill_matrix()
    drills = {drill["id"]: drill for drill in matrix["drills"]}

    assert matrix["schema_version"] == 1
    assert matrix["name"] == "team-cloud-chaos-drills-v0"
    assert {"spicedb_outage", "minio_write_failure", "postgres_readonly"} <= set(drills)
    assert drills["spicedb_outage"]["expected_behavior"] == "fail_closed"
    assert "authorization_unavailable" in drills["spicedb_outage"]["acceptance"]
    assert "backup_restore_drill" in drills["postgres_readonly"]["recovery_evidence"]
    assert all(drill["rollback_command"] for drill in matrix["drills"])


def test_chaos_drills_artifact_script_docs_and_smoke_are_registered():
    from team_cloud.chaos import build_chaos_drill_matrix

    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    doc = DOC.read_text(encoding="utf-8")
    script = SCRIPT.read_text(encoding="utf-8")
    smoke = SMOKE_SCRIPT.read_text(encoding="utf-8")
    matrix = json.loads(SMOKE_MATRIX.read_text(encoding="utf-8"))
    domains = {entry["domain"] for entry in matrix["checks"]}

    assert artifact == build_chaos_drill_matrix()
    assert os.access(SCRIPT, os.X_OK)
    assert "team-cloud-chaos-drills-v0.json" in script
    assert "spicedb_outage" in doc
    assert "postgres_readonly" in doc
    assert "tests/team_cloud/test_chaos_drills.py" in smoke
    assert "chaos_drills" in domains
