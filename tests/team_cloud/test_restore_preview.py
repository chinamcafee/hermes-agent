from __future__ import annotations

from datetime import UTC, datetime


NOW = datetime(2026, 5, 22, 12, 0, tzinfo=UTC)
ORG_KEY = b"1" * 32


def test_restore_preview_stages_create_skip_and_conflict_without_mutating_memory():
    from team_cloud.backup.restore import RestorePreviewService
    from team_cloud.memory.service import InMemoryMemoryService

    export = _encrypted_backup(
        [
            "Same checksum memory.",
            "Currently deleted memory.",
            "New memory from backup.",
        ]
    )
    target_memory = InMemoryMemoryService()
    same = target_memory.create_memory(
        {
            "org_id": "org-1",
            "scope": "personal",
            "subject_member_id": "alice",
            "content": "Same checksum memory.",
        }
    )
    deleted = target_memory.create_memory(
        {
            "org_id": "org-1",
            "scope": "personal",
            "subject_member_id": "alice",
            "content": "Currently deleted memory.",
        }
    )
    target_memory.delete_memory(deleted["id"])
    before_items = dict(target_memory.items)
    service = RestorePreviewService(
        memory_service=target_memory,
        key_resolver=_key_resolver,
        now=lambda: NOW,
        preview_id_factory=lambda: "restore-preview-1",
    )

    preview = service.preview_personal_restore(
        org_id="org-1",
        member_id="alice",
        encrypted_bytes=export.encrypted_bytes,
        manifest=export.manifest,
    )

    assert preview["id"] == "restore-preview-1"
    assert preview["status"] == "previewed"
    assert preview["backup_id"] == "backup-preview"
    assert preview["summary"] == {
        "total": 3,
        "create": 1,
        "skip": 1,
        "conflict": 1,
        "overwrite": 0,
    }
    by_content = {item["source"]["content"]: item for item in preview["items"]}
    assert by_content["Same checksum memory."]["action"] == "skip"
    assert by_content["Same checksum memory."]["reason"] == "checksum_match"
    assert by_content["Same checksum memory."]["current_memory_id"] == same["id"]
    assert by_content["Currently deleted memory."]["action"] == "conflict"
    assert by_content["Currently deleted memory."]["reason"] == "current_deleted"
    assert by_content["Currently deleted memory."]["default_strategy"] == "ask_user"
    assert by_content["New memory from backup."]["action"] == "create"
    assert by_content["New memory from backup."]["reason"] == "new_memory"
    assert target_memory.items == before_items
    assert service.previews["restore-preview-1"] == preview


def test_restore_preview_rejects_checksum_mismatch_before_staging():
    import pytest

    from team_cloud.backup.restore import RestorePreviewService
    from team_cloud.memory.service import InMemoryMemoryService

    export = _encrypted_backup(["Memory to restore."])
    tampered_manifest = dict(export.manifest)
    tampered_manifest["checksum_sha256"] = "0" * 64
    service = RestorePreviewService(
        memory_service=InMemoryMemoryService(),
        key_resolver=_key_resolver,
        now=lambda: NOW,
    )

    with pytest.raises(ValueError, match="checksum_mismatch"):
        service.preview_personal_restore(
            org_id="org-1",
            member_id="alice",
            encrypted_bytes=export.encrypted_bytes,
            manifest=tampered_manifest,
        )


def _encrypted_backup(contents: list[str]):
    from team_cloud.backup.exporter import PersonalMemoryBackupExporter
    from team_cloud.memory.service import InMemoryMemoryService

    source_memory = InMemoryMemoryService()
    for content in contents:
        source_memory.create_memory(
            {
                "org_id": "org-1",
                "scope": "personal",
                "subject_member_id": "alice",
                "content": content,
            }
        )
    exporter = PersonalMemoryBackupExporter(
        memory_service=source_memory,
        key_resolver=_key_resolver,
        now=lambda: NOW,
        backup_id_factory=lambda: "backup-preview",
    )
    return exporter.export_personal_memory(
        org_id="org-1",
        member_id="alice",
        policy={"encryption_mode": "org_managed"},
    )


def _key_resolver(org_id: str):
    from team_cloud.backup.exporter import BackupEncryptionKey

    return BackupEncryptionKey(key_id=f"{org_id}-key", key=ORG_KEY)
