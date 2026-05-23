from __future__ import annotations

from datetime import UTC, datetime, timedelta
import hashlib


NOW = datetime(2026, 5, 22, 12, 0, tzinfo=UTC)


def test_personal_backup_storage_uploads_export_and_creates_job_with_signed_url():
    import pytest

    from team_cloud.backup.exporter import BackupExportResult
    from team_cloud.backup.storage import PersonalBackupStorageService
    from team_cloud.storage.minio import InMemoryObjectStore, ObjectManifestService

    object_store = InMemoryObjectStore()
    manifest_service = ObjectManifestService(object_store=object_store)
    storage_service = PersonalBackupStorageService(
        manifest_service=manifest_service,
        now=lambda: NOW,
    )
    encrypted_bytes = b"encrypted backup bytes"
    export = BackupExportResult(
        backup_id="backup-1",
        encrypted_bytes=encrypted_bytes,
        manifest={
            "object_id": "backup-1",
            "backup_id": "backup-1",
            "org_id": "org-1",
            "owner_member_id": "alice",
            "member_id": "alice",
            "content_type": "application/zip",
            "item_count": 2,
            "checksum_sha256": hashlib.sha256(encrypted_bytes).hexdigest(),
            "encryption": {
                "mode": "org_managed",
                "algorithm": "AES-256-GCM",
                "key_id": "org-key-1",
            },
            "retention": {"policy": "member_controlled", "retention_count": 8},
        },
    )

    uploaded = storage_service.upload_export(export, policy_id="backup-policy-1")

    manifest = uploaded["manifest"]
    job = uploaded["job"]
    assert manifest["bucket"] == "hermes-personal-backups"
    assert manifest["object_key"] == (
        "org/org-1/member/alice/personal-memory/2026/05/backup-1/backup.zip.enc"
    )
    assert manifest["status"] == "active"
    assert manifest["checksum_sha256"] == hashlib.sha256(encrypted_bytes).hexdigest()
    assert manifest["encryption"]["key_id"] == "org-key-1"
    assert object_store.objects[(manifest["bucket"], manifest["object_key"])] == encrypted_bytes
    assert job["id"] == "backup-job-1"
    assert job["policy_id"] == "backup-policy-1"
    assert job["status"] == "succeeded"
    assert job["object_manifest_id"] == "backup-1"
    assert job["item_count"] == 2

    url = storage_service.signed_download_url(
        org_id="org-1",
        member_id="alice",
        backup_id="backup-1",
        expires_in=timedelta(minutes=5),
    )

    assert url.startswith("memory://hermes-personal-backups/")
    assert "backup-1/backup.zip.enc" in url
    with pytest.raises(ValueError, match="backup_owner_mismatch"):
        storage_service.signed_download_url(
            org_id="org-1",
            member_id="bob",
            backup_id="backup-1",
            expires_in=timedelta(minutes=5),
        )
    with pytest.raises(ValueError, match="presigned URL TTL"):
        storage_service.signed_download_url(
            org_id="org-1",
            member_id="alice",
            backup_id="backup-1",
            expires_in=timedelta(minutes=6),
        )


def test_personal_backup_storage_retention_cleanup_deletes_old_backups_only():
    from team_cloud.backup.exporter import BackupExportResult
    from team_cloud.backup.storage import PersonalBackupStorageService
    from team_cloud.storage.minio import InMemoryObjectStore, ObjectManifestService

    object_store = InMemoryObjectStore()
    storage_service = PersonalBackupStorageService(
        manifest_service=ObjectManifestService(object_store=object_store),
        now=lambda: NOW,
    )
    for index, created_at in enumerate(
        (
            datetime(2026, 5, 20, 12, 0, tzinfo=UTC),
            datetime(2026, 5, 21, 12, 0, tzinfo=UTC),
            datetime(2026, 5, 22, 12, 0, tzinfo=UTC),
        ),
        start=1,
    ):
        storage_service.upload_export(
            _export(f"backup-{index}", member_id="alice"),
            created_at=created_at,
        )
    storage_service.upload_export(
        _export("backup-other-member", member_id="bob"),
        created_at=datetime(2026, 5, 19, 12, 0, tzinfo=UTC),
    )

    deleted = storage_service.cleanup_retention(
        org_id="org-1",
        member_id="alice",
        retention_count=2,
    )

    assert deleted == ["backup-1"]
    assert storage_service.manifest_service.manifests["backup-1"]["status"] == "deleted"
    assert storage_service.manifest_service.manifests["backup-1"]["deleted_at"] is not None
    assert "backup-1" not in {
        key[1].split("/")[-2] for key in object_store.objects
    }
    assert [item["object_id"] for item in storage_service.list_member_backups(
        org_id="org-1",
        member_id="alice",
    )] == ["backup-3", "backup-2"]
    assert storage_service.manifest_service.manifests["backup-other-member"]["status"] == "active"


def _export(backup_id: str, *, member_id: str) -> BackupExportResult:
    from team_cloud.backup.exporter import BackupExportResult

    content = f"encrypted {backup_id}".encode("utf-8")
    return BackupExportResult(
        backup_id=backup_id,
        encrypted_bytes=content,
        manifest={
            "object_id": backup_id,
            "backup_id": backup_id,
            "org_id": "org-1",
            "owner_member_id": member_id,
            "member_id": member_id,
            "content_type": "application/zip",
            "item_count": 1,
            "checksum_sha256": hashlib.sha256(content).hexdigest(),
            "encryption": {
                "mode": "org_managed",
                "algorithm": "AES-256-GCM",
                "key_id": "org-key-1",
            },
            "retention": {"policy": "member_controlled", "retention_count": 2},
        },
    )
