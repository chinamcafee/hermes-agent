from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from zipfile import ZipFile
from io import BytesIO


NOW = datetime(2026, 5, 22, 12, 0, tzinfo=UTC)
ORG_KEY = b"0" * 32


def test_personal_backup_exporter_builds_encrypted_zip_and_manifest():
    from team_cloud.backup.exporter import (
        BackupEncryptionKey,
        PersonalMemoryBackupExporter,
        decrypt_backup_package,
    )
    from team_cloud.memory.service import InMemoryMemoryService

    memory_service = InMemoryMemoryService()
    personal = memory_service.create_memory(
        {
            "org_id": "org-1",
            "scope": "personal",
            "subject_member_id": "alice",
            "content": "Remember Alice prefers concise summaries.",
        }
    )
    memory_service.create_memory(
        {
            "org_id": "org-1",
            "scope": "personal",
            "subject_member_id": "bob",
            "content": "Bob memory must stay out.",
        }
    )
    memory_service.create_memory(
        {
            "org_id": "org-1",
            "scope": "team_shared",
            "team_id": "team-1",
            "content": "Team memory must stay out.",
        }
    )
    exporter = PersonalMemoryBackupExporter(
        memory_service=memory_service,
        key_resolver=lambda org_id: BackupEncryptionKey(
            key_id=f"{org_id}-key-1",
            key=ORG_KEY,
        ),
        now=lambda: NOW,
        backup_id_factory=lambda: "backup-1",
    )

    result = exporter.export_personal_memory(
        org_id="org-1",
        member_id="alice",
        policy={
            "retention_count": 8,
            "include_deleted": False,
            "include_archived": False,
            "include_embeddings": False,
            "encryption_mode": "org_managed",
        },
    )

    assert result.backup_id == "backup-1"
    assert result.encrypted_bytes[:2] != b"PK"
    assert result.manifest["object_type"] == "personal_backup"
    assert result.manifest["org_id"] == "org-1"
    assert result.manifest["owner_member_id"] == "alice"
    assert result.manifest["checksum_sha256"] == hashlib.sha256(
        result.encrypted_bytes
    ).hexdigest()
    assert result.manifest["encryption"]["mode"] == "org_managed"
    assert result.manifest["encryption"]["key_id"] == "org-1-key-1"

    plaintext_zip = decrypt_backup_package(
        result.encrypted_bytes,
        manifest=result.manifest,
        key_resolver=lambda org_id: BackupEncryptionKey(
            key_id=f"{org_id}-key-1",
            key=ORG_KEY,
        ),
    )
    with ZipFile(BytesIO(plaintext_zip)) as archive:
        assert set(archive.namelist()) == {
            "manifest.json",
            "memories.jsonl",
            "memory_events.jsonl",
            "README.md",
        }
        package_manifest = json.loads(archive.read("manifest.json"))
        memories = [
            json.loads(line)
            for line in archive.read("memories.jsonl").decode("utf-8").splitlines()
        ]
        events = [
            json.loads(line)
            for line in archive.read("memory_events.jsonl").decode("utf-8").splitlines()
        ]

    assert package_manifest["backup_id"] == "backup-1"
    assert package_manifest["item_count"] == 1
    assert package_manifest["event_count"] == 1
    assert [memory["id"] for memory in memories] == [personal["id"]]
    assert events[0]["memory_id"] == personal["id"]


def test_personal_backup_exporter_honors_include_flags_and_strips_embeddings():
    from team_cloud.backup.exporter import (
        BackupEncryptionKey,
        PersonalMemoryBackupExporter,
        decrypt_backup_package,
    )
    from team_cloud.memory.service import InMemoryMemoryService

    memory_service = InMemoryMemoryService()
    active = memory_service.create_memory(
        {
            "org_id": "org-1",
            "scope": "personal",
            "subject_member_id": "alice",
            "content": "Active memory.",
        }
    )
    deleted = memory_service.create_memory(
        {
            "org_id": "org-1",
            "scope": "personal",
            "subject_member_id": "alice",
            "content": "Deleted memory.",
        }
    )
    archived = memory_service.create_memory(
        {
            "org_id": "org-1",
            "scope": "personal",
            "subject_member_id": "alice",
            "content": "Archived memory.",
        }
    )
    memory_service.items[active["id"]]["embedding"] = [0.1, 0.2]
    memory_service.items[active["id"]]["embedding_vector"] = [0.3, 0.4]
    memory_service.delete_memory(deleted["id"])
    memory_service.archive_memory(archived["id"])
    exporter = PersonalMemoryBackupExporter(
        memory_service=memory_service,
        key_resolver=lambda org_id: BackupEncryptionKey("key-1", ORG_KEY),
        now=lambda: NOW,
        backup_id_factory=lambda: "backup-2",
    )

    result = exporter.export_personal_memory(
        org_id="org-1",
        member_id="alice",
        policy={
            "include_deleted": True,
            "include_archived": False,
            "include_embeddings": False,
            "encryption_mode": "org_managed",
        },
    )

    plaintext_zip = decrypt_backup_package(
        result.encrypted_bytes,
        manifest=result.manifest,
        key_resolver=lambda org_id: BackupEncryptionKey("key-1", ORG_KEY),
    )
    with ZipFile(BytesIO(plaintext_zip)) as archive:
        memories = [
            json.loads(line)
            for line in archive.read("memories.jsonl").decode("utf-8").splitlines()
        ]

    assert {memory["id"] for memory in memories} == {active["id"], deleted["id"]}
    assert all(memory["id"] != archived["id"] for memory in memories)
    assert all("embedding" not in memory for memory in memories)
    assert all("embedding_vector" not in memory for memory in memories)


def test_user_passphrase_export_does_not_require_org_key_and_rejects_bad_passphrase():
    import pytest

    from team_cloud.backup.exporter import (
        PersonalMemoryBackupExporter,
        decrypt_backup_package,
    )
    from team_cloud.memory.service import InMemoryMemoryService

    memory_service = InMemoryMemoryService()
    memory_service.create_memory(
        {
            "org_id": "org-1",
            "scope": "personal",
            "subject_member_id": "alice",
            "content": "Passphrase-protected memory.",
        }
    )
    exporter = PersonalMemoryBackupExporter(
        memory_service=memory_service,
        key_resolver=None,
        now=lambda: NOW,
        backup_id_factory=lambda: "backup-3",
    )

    with pytest.raises(ValueError, match="passphrase_required"):
        exporter.export_personal_memory(
            org_id="org-1",
            member_id="alice",
            policy={"encryption_mode": "user_passphrase"},
        )

    result = exporter.export_personal_memory(
        org_id="org-1",
        member_id="alice",
        policy={"encryption_mode": "user_passphrase"},
        passphrase="correct horse battery staple",
    )

    assert result.manifest["encryption"]["mode"] == "user_passphrase"
    assert "encrypted_data_key" not in result.manifest["encryption"]
    assert decrypt_backup_package(
        result.encrypted_bytes,
        manifest=result.manifest,
        passphrase="correct horse battery staple",
    ).startswith(b"PK")
    with pytest.raises(ValueError, match="backup_decryption_failed"):
        decrypt_backup_package(
            result.encrypted_bytes,
            manifest=result.manifest,
            passphrase="wrong",
        )
