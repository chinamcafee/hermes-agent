from __future__ import annotations

from datetime import UTC, datetime, timedelta


def test_minio_bucket_bootstrap_creates_private_buckets():
    from team_cloud.storage.minio import InMemoryObjectStore, ObjectManifestService

    store = InMemoryObjectStore()
    service = ObjectManifestService(object_store=store)

    created = service.bootstrap_buckets()

    assert created == [
        "hermes-personal-backups",
        "hermes-org-exports",
        "hermes-attachments",
        "hermes-document-sources",
        "hermes-restore-staging",
    ]
    assert all(bucket["policy"] == "private" for bucket in store.buckets.values())


def test_upload_personal_backup_writes_object_and_manifest():
    from team_cloud.storage.minio import InMemoryObjectStore, ObjectManifestService

    store = InMemoryObjectStore()
    service = ObjectManifestService(object_store=store)
    created_at = datetime(2026, 5, 22, 12, 0, tzinfo=UTC)

    manifest = service.upload_object(
        object_type="personal_backup",
        org_id="org-1",
        owner_member_id="member-1",
        content=b"encrypted backup bytes",
        content_type="application/zip",
        object_id="backup-1",
        created_at=created_at,
        encryption={"mode": "org_managed", "algorithm": "AES-256-GCM", "key_id": "key-1"},
        retention={
            "policy": "member_controlled",
            "delete_after": None,
            "legal_hold": False,
        },
    )

    assert manifest["bucket"] == "hermes-personal-backups"
    assert manifest["object_key"] == (
        "org/org-1/member/member-1/personal-memory/2026/05/backup-1/backup.zip.enc"
    )
    assert manifest["size_bytes"] == len(b"encrypted backup bytes")
    assert len(manifest["checksum_sha256"]) == 64
    assert store.objects[(manifest["bucket"], manifest["object_key"])] == b"encrypted backup bytes"
    assert service.manifests[manifest["object_id"]] == manifest


def test_manifest_signed_url_is_short_lived_and_uses_object_key():
    from team_cloud.storage.minio import InMemoryObjectStore, ObjectManifestService

    service = ObjectManifestService(object_store=InMemoryObjectStore())
    manifest = service.upload_object(
        object_type="attachment",
        org_id="org-1",
        session_id="session-1",
        content=b"blob",
        content_type="application/octet-stream",
        object_id="attachment-1",
        created_at=datetime(2026, 5, 22, tzinfo=UTC),
        retention={"policy": "none", "delete_after": None, "legal_hold": False},
    )

    url = service.presigned_get_url(
        manifest["object_id"],
        expires_in=timedelta(minutes=5),
    )

    assert url.startswith("memory://hermes-attachments/")
    assert "org/org-1/session/session-1/attachments/attachment-1/blob.bin" in url
    assert "expires_in=300" in url


def test_manifest_rejects_missing_required_owner_for_personal_backup():
    import pytest

    from team_cloud.storage.minio import InMemoryObjectStore, ObjectManifestService

    service = ObjectManifestService(object_store=InMemoryObjectStore())

    with pytest.raises(ValueError, match="owner_member_id is required"):
        service.upload_object(
            object_type="personal_backup",
            org_id="org-1",
            content=b"backup",
            content_type="application/zip",
            object_id="backup-1",
        )
