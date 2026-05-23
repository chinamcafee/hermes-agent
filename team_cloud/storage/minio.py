"""MinIO-compatible object store and manifest helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
import hashlib
from typing import Any, Literal


ObjectType = Literal[
    "personal_backup",
    "org_export",
    "attachment",
    "document_source",
    "restore_staging",
]

BUCKETS_BY_OBJECT_TYPE: dict[str, str] = {
    "personal_backup": "hermes-personal-backups",
    "org_export": "hermes-org-exports",
    "attachment": "hermes-attachments",
    "document_source": "hermes-document-sources",
    "restore_staging": "hermes-restore-staging",
}


@dataclass
class InMemoryObjectStore:
    buckets: dict[str, dict[str, str]] = field(default_factory=dict)
    objects: dict[tuple[str, str], bytes] = field(default_factory=dict)

    def ensure_bucket(self, bucket: str) -> None:
        self.buckets.setdefault(bucket, {"name": bucket, "policy": "private"})

    def put_object(self, *, bucket: str, object_key: str, content: bytes) -> None:
        if bucket not in self.buckets:
            self.ensure_bucket(bucket)
        self.objects[(bucket, object_key)] = content

    def delete_object(self, *, bucket: str, object_key: str) -> bool:
        return self.objects.pop((bucket, object_key), None) is not None

    def presigned_get_url(
        self,
        *,
        bucket: str,
        object_key: str,
        expires_in: timedelta,
    ) -> str:
        seconds = int(expires_in.total_seconds())
        return f"memory://{bucket}/{object_key}?expires_in={seconds}"


@dataclass
class ObjectManifestService:
    object_store: InMemoryObjectStore
    manifests: dict[str, dict[str, Any]] = field(default_factory=dict)

    def bootstrap_buckets(self) -> list[str]:
        for bucket in BUCKETS_BY_OBJECT_TYPE.values():
            self.object_store.ensure_bucket(bucket)
        return list(BUCKETS_BY_OBJECT_TYPE.values())

    def upload_object(
        self,
        *,
        object_type: ObjectType,
        org_id: str,
        content: bytes,
        content_type: str,
        object_id: str,
        created_at: datetime | None = None,
        owner_member_id: str | None = None,
        team_id: str | None = None,
        project_id: str | None = None,
        session_id: str | None = None,
        document_id: str | None = None,
        encryption: dict[str, Any] | None = None,
        retention: dict[str, Any] | None = None,
        source: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        created_at = created_at or datetime.now(UTC)
        bucket = BUCKETS_BY_OBJECT_TYPE[object_type]
        object_key = _object_key(
            object_type=object_type,
            org_id=org_id,
            object_id=object_id,
            created_at=created_at,
            owner_member_id=owner_member_id,
            session_id=session_id,
            document_id=document_id,
        )
        manifest = {
            "schema_version": 1,
            "object_type": object_type,
            "object_id": object_id,
            "org_id": org_id,
            "owner_member_id": owner_member_id,
            "team_id": team_id,
            "project_id": project_id,
            "session_id": session_id,
            "document_id": document_id,
            "bucket": bucket,
            "object_key": object_key,
            "content_type": content_type,
            "size_bytes": len(content),
            "checksum_sha256": hashlib.sha256(content).hexdigest(),
            "encryption": encryption or _default_encryption(),
            "retention": retention or _default_retention(),
            "source": source or {},
            "status": "active",
            "created_at": created_at.isoformat(),
            "deleted_at": None,
        }
        _validate_manifest(manifest)
        self.bootstrap_buckets()
        self.object_store.put_object(bucket=bucket, object_key=object_key, content=content)
        self.manifests[object_id] = manifest
        return manifest

    def mark_deleted(
        self,
        object_id: str,
        *,
        deleted_at: datetime | None = None,
    ) -> dict[str, Any]:
        deleted_at = deleted_at or datetime.now(UTC)
        manifest = self.manifests[object_id]
        self.object_store.delete_object(
            bucket=manifest["bucket"],
            object_key=manifest["object_key"],
        )
        manifest["status"] = "deleted"
        manifest["deleted_at"] = deleted_at.isoformat()
        return manifest

    def presigned_get_url(
        self,
        object_id: str,
        *,
        expires_in: timedelta,
    ) -> str:
        if expires_in > timedelta(minutes=5):
            raise ValueError("presigned URL TTL must be <= 5 minutes")
        manifest = self.manifests[object_id]
        return self.object_store.presigned_get_url(
            bucket=manifest["bucket"],
            object_key=manifest["object_key"],
            expires_in=expires_in,
        )


def _object_key(
    *,
    object_type: str,
    org_id: str,
    object_id: str,
    created_at: datetime,
    owner_member_id: str | None,
    session_id: str | None,
    document_id: str | None,
) -> str:
    year = f"{created_at.year:04d}"
    month = f"{created_at.month:02d}"
    if object_type == "personal_backup":
        if owner_member_id is None:
            raise ValueError("owner_member_id is required for personal_backup")
        return (
            f"org/{org_id}/member/{owner_member_id}/personal-memory/"
            f"{year}/{month}/{object_id}/backup.zip.enc"
        )
    if object_type == "org_export":
        return f"org/{org_id}/exports/{year}/{month}/{object_id}/export.zip.enc"
    if object_type == "attachment":
        if session_id is None:
            raise ValueError("session_id is required for attachment")
        return f"org/{org_id}/session/{session_id}/attachments/{object_id}/blob.bin"
    if object_type == "document_source":
        if document_id is None:
            raise ValueError("document_id is required for document_source")
        return f"org/{org_id}/documents/{document_id}/source/{object_id}/source.bin"
    if object_type == "restore_staging":
        if owner_member_id is None:
            raise ValueError("owner_member_id is required for restore_staging")
        return f"org/{org_id}/member/{owner_member_id}/restore/{object_id}/staging.zip.enc"
    raise ValueError(f"unsupported object_type: {object_type}")


def _validate_manifest(manifest: dict[str, Any]) -> None:
    required = {
        "schema_version",
        "object_type",
        "object_id",
        "org_id",
        "bucket",
        "object_key",
        "content_type",
        "size_bytes",
        "checksum_sha256",
        "encryption",
        "retention",
        "created_at",
    }
    missing = sorted(required.difference(manifest))
    if missing:
        raise ValueError(f"manifest missing required fields: {missing}")
    if len(manifest["checksum_sha256"]) != 64:
        raise ValueError("manifest checksum_sha256 must be sha256 hex")


def _default_encryption() -> dict[str, Any]:
    return {"mode": "none", "algorithm": "none", "key_id": None}


def _default_retention() -> dict[str, Any]:
    return {"policy": "none", "delete_after": None, "legal_hold": False}
