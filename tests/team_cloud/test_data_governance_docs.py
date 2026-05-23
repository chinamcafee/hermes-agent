from __future__ import annotations

from pathlib import Path


DOC = Path("teamDoc/GADoc/P3-20-data-governance-runbooks.md")
SMOKE_SCRIPT = Path("scripts/team-cloud-foundation-smoke.sh")


def test_data_governance_runbooks_cover_core_flows_and_entrypoints():
    content = DOC.read_text(encoding="utf-8")

    assert "# P3-20 数据治理 Runbook" in content
    for heading in (
        "## Personal Backup Runbook",
        "## Organization Export Runbook",
        "## Deletion Request Runbook",
        "## Break-glass Runbook",
        "## Audit And Evidence",
        "## Failure Handling",
    ):
        assert heading in content

    for expected in (
        "PersonalBackupRestoreDrill",
        "OrganizationExportService",
        "DeletionRequestService",
        "HardDeleteWorker",
        "BreakGlassService",
        "/api/audit/export",
        "checksum_mismatch",
        "authorization_unavailable",
        "relationship_outbox_dead_letter",
    ):
        assert expected in content


def test_data_governance_runbooks_include_operator_checklists_and_validation():
    content = DOC.read_text(encoding="utf-8")

    for checklist_heading in (
        "Pre-checks",
        "Execution",
        "Validation",
        "Rollback / Recovery",
        "Evidence",
    ):
        assert checklist_heading in content

    for validation_artifact in (
        "scripts/team-cloud-foundation-smoke.sh",
        "tests/team_cloud/test_backup_restore_drill.py",
        "tests/team_cloud/test_org_export.py",
        "tests/team_cloud/test_deletion_request.py",
        "tests/team_cloud/test_hard_delete_worker.py",
        "tests/team_cloud/test_break_glass.py",
        "tests/team_cloud/test_authz_chaos.py",
    ):
        assert validation_artifact in content


def test_foundation_smoke_includes_data_governance_docs_check():
    content = SMOKE_SCRIPT.read_text(encoding="utf-8")

    assert "tests/team_cloud/test_data_governance_docs.py" in content
