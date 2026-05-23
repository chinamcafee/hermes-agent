from __future__ import annotations

from datetime import UTC, datetime


NOW = datetime(2026, 5, 22, 12, 0, tzinfo=UTC)
ORG_KEY = b"2" * 32


def test_personal_backup_restore_drill_uploads_downloads_previews_and_executes():
    from team_cloud.backup.drill import PersonalBackupRestoreDrill
    from team_cloud.memory.service import InMemoryMemoryService

    source_memory = InMemoryMemoryService()
    target_memory = InMemoryMemoryService()
    first = source_memory.create_memory(
        {
            "org_id": "org-1",
            "scope": "personal",
            "subject_member_id": "alice",
            "content": "Alice prefers concise summaries.",
        }
    )
    second = source_memory.create_memory(
        {
            "org_id": "org-1",
            "scope": "personal",
            "subject_member_id": "alice",
            "content": "Alice uses weekly backup reports.",
        }
    )
    source_memory.create_memory(
        {
            "org_id": "org-1",
            "scope": "personal",
            "subject_member_id": "bob",
            "content": "Bob must stay out of Alice backup.",
        }
    )
    drill = PersonalBackupRestoreDrill(
        key_resolver=_key_resolver,
        now=lambda: NOW,
        backup_id_factory=lambda: "backup-drill-1",
        preview_id_factory=lambda: "restore-preview-drill-1",
    )

    evidence = drill.run_single_member_restore(
        source_memory_service=source_memory,
        target_memory_service=target_memory,
        org_id="org-1",
        member_id="alice",
        actor_member_id="alice",
    )

    assert evidence["status"] == "succeeded"
    assert evidence["backup_id"] == "backup-drill-1"
    assert evidence["signed_download_url"].startswith("memory://hermes-personal-backups/")
    assert evidence["object_manifest"]["status"] == "active"
    assert evidence["preview"]["summary"] == {
        "total": 2,
        "create": 2,
        "skip": 0,
        "conflict": 0,
        "overwrite": 0,
    }
    assert evidence["restore_job"]["status"] == "succeeded"
    assert evidence["restore_job"]["summary"]["created"] == 2
    assert set(evidence["restored_source_memory_ids"]) == {first["id"], second["id"]}
    assert {
        memory["content"] for memory in target_memory.list_memory(org_id="org-1")
    } == {
        "Alice prefers concise summaries.",
        "Alice uses weekly backup reports.",
    }


def test_personal_backup_restore_drill_blocks_checksum_mismatch_before_restore():
    from team_cloud.backup.drill import PersonalBackupRestoreDrill
    from team_cloud.memory.service import InMemoryMemoryService

    source_memory = InMemoryMemoryService()
    target_memory = InMemoryMemoryService()
    source_memory.create_memory(
        {
            "org_id": "org-1",
            "scope": "personal",
            "subject_member_id": "alice",
            "content": "Checksum mismatch must not restore.",
        }
    )
    drill = PersonalBackupRestoreDrill(
        key_resolver=_key_resolver,
        now=lambda: NOW,
        backup_id_factory=lambda: "backup-drill-mismatch",
    )

    evidence = drill.run_checksum_mismatch_guard(
        source_memory_service=source_memory,
        target_memory_service=target_memory,
        org_id="org-1",
        member_id="alice",
    )

    assert evidence["status"] == "blocked"
    assert evidence["error"] == "checksum_mismatch"
    assert evidence["preview_created"] is False
    assert evidence["restore_job_created"] is False
    assert target_memory.list_memory(org_id="org-1") == []


def _key_resolver(org_id: str):
    from team_cloud.backup.exporter import BackupEncryptionKey

    return BackupEncryptionKey(key_id=f"{org_id}-key", key=ORG_KEY)
