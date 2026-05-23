from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path


NOW = datetime(2026, 5, 23, 9, 30, tzinfo=UTC)
ORG_KEY = b"3" * 32
ARTIFACT = Path("teamDoc/GADoc/artifacts/drills/team-cloud-backup-restore-drill-v0.json")
DOC = Path("teamDoc/GADoc/P4-06-backup-restore-drill.md")
SMOKE_SCRIPT = Path("scripts/team-cloud-foundation-smoke.sh")
SMOKE_MATRIX = Path("teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json")

REQUIRED_RESTORE_DOMAINS = {
    "postgresql_pitr",
    "spicedb_relationship_snapshot",
    "minio_bucket_restore",
    "casdoor_config_restore",
    "personal_memory_restore",
    "org_export_rehydrate",
}


def test_platform_backup_restore_drill_report_covers_all_ga_restore_domains():
    from team_cloud.backup.drill import PlatformBackupRestoreDrill
    from team_cloud.memory.service import InMemoryMemoryService

    source_memory = InMemoryMemoryService()
    target_memory = InMemoryMemoryService()
    source_memory.create_memory(
        {
            "org_id": "org-1",
            "scope": "personal",
            "subject_member_id": "alice",
            "content": "Alice wants backup drill evidence in the beta report.",
        }
    )
    drill = PlatformBackupRestoreDrill(
        key_resolver=_key_resolver,
        now=lambda: NOW,
        drill_id_factory=lambda: "platform-drill-1",
        backup_id_factory=lambda: "backup-platform-drill-1",
        preview_id_factory=lambda: "restore-preview-platform-drill-1",
    )

    report = drill.run_platform_restore_drill(
        source_memory_service=source_memory,
        target_memory_service=target_memory,
        org_id="org-1",
        member_id="alice",
        actor_member_id="alice",
        snapshot_ids={
            "postgresql": "pg-snapshot-20260523",
            "spicedb": "spicedb-snapshot-20260523",
            "minio": "minio-snapshot-20260523",
            "casdoor": "casdoor-export-20260523",
            "org_export": "org-export-20260523",
        },
        outbox_replay_count=7,
        minio_object_count=4,
    )

    assert report["schema_version"] == 1
    assert report["drill_id"] == "platform-drill-1"
    assert report["status"] == "succeeded"
    assert report["generated_at"] == "2026-05-23T09:30:00Z"
    assert {component["domain"] for component in report["components"]} == (
        REQUIRED_RESTORE_DOMAINS
    )
    assert all(component["status"] == "succeeded" for component in report["components"])
    assert all(component["backup_artifact"] for component in report["components"])
    assert all(component["restore_action"] for component in report["components"])
    assert all(component["validation_checks"] for component in report["components"])

    personal = _component(report, "personal_memory_restore")
    assert personal["evidence"]["backup_id"] == "backup-platform-drill-1"
    assert personal["evidence"]["restore_job"]["status"] == "succeeded"
    assert personal["evidence"]["restore_job"]["summary"]["created"] == 1
    assert personal["evidence"]["embedding_rebuild_requested"]

    spicedb = _component(report, "spicedb_relationship_snapshot")
    assert spicedb["evidence"]["outbox_replay_count"] == 7
    assert spicedb["validation_checks"][-1]["name"] == "outbox_replay_idempotent"

    minio = _component(report, "minio_bucket_restore")
    assert minio["evidence"]["object_count"] == 4


def test_platform_backup_restore_drill_artifact_docs_and_smoke_are_registered():
    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    doc = DOC.read_text(encoding="utf-8")
    script = SMOKE_SCRIPT.read_text(encoding="utf-8")
    matrix = json.loads(SMOKE_MATRIX.read_text(encoding="utf-8"))
    domains = {entry["domain"] for entry in matrix["checks"]}

    assert artifact["schema_version"] == 1
    assert artifact["status"] == "succeeded"
    assert {component["domain"] for component in artifact["components"]} == (
        REQUIRED_RESTORE_DOMAINS
    )
    assert "PostgreSQL PITR" in doc
    assert "SpiceDB relationship snapshot" in doc
    assert "MinIO bucket restore" in doc
    assert "Casdoor config restore" in doc
    assert "tests/team_cloud/test_platform_backup_restore_drill.py" in script
    assert "platform_backup_restore_drill" in domains
    assert os.access(Path("scripts/team-cloud-backup-restore-drill.py"), os.X_OK)


def _component(report: dict, domain: str) -> dict:
    return next(component for component in report["components"] if component["domain"] == domain)


def _key_resolver(org_id: str):
    from team_cloud.backup.exporter import BackupEncryptionKey

    return BackupEncryptionKey(key_id=f"{org_id}-key", key=ORG_KEY)
