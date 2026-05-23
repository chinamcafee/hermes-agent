from __future__ import annotations

import json
import os
from pathlib import Path


ARTIFACT = Path("teamDoc/GADoc/artifacts/release/team-cloud-runbook-summary-v0.json")
DOC = Path("teamDoc/GADoc/P5-06-runbook-summary.md")
SCRIPT = Path("scripts/team-cloud-runbook-summary.py")
SMOKE_SCRIPT = Path("scripts/team-cloud-foundation-smoke.sh")
SMOKE_MATRIX = Path("teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json")


def test_runbook_summary_covers_ga_outage_backup_upgrade_and_security_alerts():
    from team_cloud.runbook_summary import build_runbook_summary_package

    package = build_runbook_summary_package()
    runbooks = {runbook["id"]: runbook for runbook in package["runbooks"]}
    drill_ids = {drill["id"] for drill in package["drill_evidence"]}

    assert package["schema_version"] == 1
    assert package["name"] == "team-cloud-runbook-summary-v0"
    assert {
        "backup_restore_failure",
        "casdoor_jwks_rotation_failure",
        "spicedb_unavailable",
        "postgres_slow_pgvector_query",
        "minio_upload_failure",
        "outbox_dead_letter",
        "upgrade_rollback",
        "cross_tenant_access_alert",
        "destructive_tool_abuse_alert",
    } <= set(runbooks)
    assert runbooks["backup_restore_failure"]["owner"] == "SRE"
    assert "scripts/team-cloud-backup-restore-drill.py" in runbooks[
        "backup_restore_failure"
    ]["commands"]
    assert "scripts/team-cloud-foundation-smoke.sh" in runbooks["upgrade_rollback"][
        "verification"
    ]
    assert {"backup_restore_drill", "authz_chaos", "upgrade_rollback"} <= drill_ids
    assert package["escalation"]["p0_p1_security_defects_allowed"] == 0


def test_runbook_summary_artifact_script_docs_and_smoke_are_registered():
    from team_cloud.runbook_summary import build_runbook_summary_package

    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    doc = DOC.read_text(encoding="utf-8")
    script = SCRIPT.read_text(encoding="utf-8")
    smoke = SMOKE_SCRIPT.read_text(encoding="utf-8")
    matrix = json.loads(SMOKE_MATRIX.read_text(encoding="utf-8"))
    domains = {entry["domain"] for entry in matrix["checks"]}

    assert artifact == build_runbook_summary_package()
    assert os.access(SCRIPT, os.X_OK)
    assert "team-cloud-runbook-summary-v0.json" in script
    assert "backup_restore_failure" in doc
    assert "spicedb_unavailable" in doc
    assert "postgres_slow_pgvector_query" in doc
    assert "upgrade_rollback" in doc
    assert "cross_tenant_access_alert" in doc
    assert "tests/team_cloud/test_runbook_summary.py" in smoke
    assert "runbook_summary" in domains
