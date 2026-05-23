"""Personal backup object upload and lifecycle helpers."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta
import hashlib
from typing import Any, Callable

from team_cloud.backup.exporter import BackupExportResult
from team_cloud.storage.minio import ObjectManifestService


class PersonalBackupStorageService:
    """Uploads encrypted backup exports and manages member retention."""

    def __init__(
        self,
        *,
        manifest_service: ObjectManifestService,
        notification_service: Any | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.manifest_service = manifest_service
        self.notification_service = notification_service
        self._now = now or (lambda: datetime.now(UTC))
        self._job_counter = 0
        self.jobs: dict[str, dict[str, Any]] = {}

    def upload_export(
        self,
        export: BackupExportResult,
        *,
        policy_id: str | None = None,
        created_at: datetime | None = None,
    ) -> dict[str, dict[str, Any]]:
        created_at = _coerce_datetime(created_at or self._now())
        export_manifest = export.manifest
        org_id = _required("org_id", export_manifest["org_id"])
        member_id = _required("owner_member_id", export_manifest["owner_member_id"])
        backup_id = _required("backup_id", export.backup_id)
        try:
            if hashlib.sha256(export.encrypted_bytes).hexdigest() != export_manifest["checksum_sha256"]:
                raise ValueError("checksum_mismatch")

            manifest = self.manifest_service.upload_object(
                object_type="personal_backup",
                org_id=org_id,
                owner_member_id=member_id,
                content=export.encrypted_bytes,
                content_type=export_manifest.get("content_type", "application/zip"),
                object_id=backup_id,
                created_at=created_at,
                encryption=deepcopy(export_manifest.get("encryption", {})),
                retention=deepcopy(export_manifest.get("retention", {})),
            )
            job = self._record_job(
                org_id=org_id,
                member_id=member_id,
                policy_id=policy_id,
                manifest=manifest,
                item_count=int(export_manifest.get("item_count", 0)),
                created_at=created_at,
            )
            return {"manifest": deepcopy(manifest), "job": deepcopy(job)}
        except Exception as exc:
            error = str(exc) or type(exc).__name__
            self._record_failed_job(
                org_id=org_id,
                member_id=member_id,
                policy_id=policy_id,
                backup_id=backup_id,
                checksum_sha256=str(export_manifest.get("checksum_sha256") or ""),
                item_count=int(export_manifest.get("item_count", 0)),
                error=error,
                created_at=created_at,
            )
            self._notify_backup_failure(
                org_id=org_id,
                member_id=member_id,
                backup_id=backup_id,
                policy_id=policy_id,
                error=error,
                channels=export_manifest.get("notification_channels"),
            )
            raise

    def signed_download_url(
        self,
        *,
        org_id: str,
        member_id: str,
        backup_id: str,
        expires_in: timedelta,
    ) -> str:
        manifest = self._require_member_manifest(
            org_id=org_id,
            member_id=member_id,
            backup_id=backup_id,
        )
        return self.manifest_service.presigned_get_url(
            manifest["object_id"],
            expires_in=expires_in,
        )

    def cleanup_retention(
        self,
        *,
        org_id: str,
        member_id: str,
        retention_count: int,
    ) -> list[str]:
        retention_count = _positive_int(retention_count)
        backups = self.list_member_backups(org_id=org_id, member_id=member_id)
        deleted: list[str] = []
        for manifest in backups[retention_count:]:
            deleted_manifest = self.manifest_service.mark_deleted(
                manifest["object_id"],
                deleted_at=self._now(),
            )
            deleted.append(deleted_manifest["object_id"])
        return deleted

    def list_member_backups(self, *, org_id: str, member_id: str) -> list[dict[str, Any]]:
        org_id = _required("org_id", org_id)
        member_id = _required("member_id", member_id)
        manifests = []
        for manifest in self.manifest_service.manifests.values():
            if manifest.get("object_type") != "personal_backup":
                continue
            if manifest.get("org_id") != org_id:
                continue
            if manifest.get("owner_member_id") != member_id:
                continue
            if manifest.get("status") != "active":
                continue
            manifests.append(deepcopy(manifest))
        return sorted(manifests, key=lambda item: item["created_at"], reverse=True)

    def _record_job(
        self,
        *,
        org_id: str,
        member_id: str,
        policy_id: str | None,
        manifest: dict[str, Any],
        item_count: int,
        created_at: datetime,
    ) -> dict[str, Any]:
        self._job_counter += 1
        timestamp = _timestamp(created_at)
        job = {
            "id": f"backup-job-{self._job_counter}",
            "org_id": org_id,
            "member_id": member_id,
            "policy_id": policy_id,
            "status": "succeeded",
            "object_manifest_id": manifest["object_id"],
            "item_count": item_count,
            "checksum_sha256": manifest["checksum_sha256"],
            "error": None,
            "created_at": timestamp,
            "started_at": timestamp,
            "finished_at": timestamp,
        }
        self.jobs[job["id"]] = job
        return job

    def _record_failed_job(
        self,
        *,
        org_id: str,
        member_id: str,
        policy_id: str | None,
        backup_id: str,
        checksum_sha256: str,
        item_count: int,
        error: str,
        created_at: datetime,
    ) -> dict[str, Any]:
        self._job_counter += 1
        timestamp = _timestamp(created_at)
        job = {
            "id": f"backup-job-{self._job_counter}",
            "org_id": org_id,
            "member_id": member_id,
            "policy_id": policy_id,
            "status": "failed",
            "object_manifest_id": backup_id,
            "item_count": item_count,
            "checksum_sha256": checksum_sha256,
            "error": error,
            "created_at": timestamp,
            "started_at": timestamp,
            "finished_at": timestamp,
        }
        self.jobs[job["id"]] = job
        return job

    def _notify_backup_failure(
        self,
        *,
        org_id: str,
        member_id: str,
        backup_id: str,
        policy_id: str | None,
        error: str,
        channels: Any,
    ) -> None:
        if self.notification_service is None:
            return
        self.notification_service.notify_backup_failure(
            org_id=org_id,
            member_id=member_id,
            backup_id=backup_id,
            policy_id=policy_id,
            error=error,
            channels=channels or ("in_app",),
        )

    def _require_member_manifest(
        self,
        *,
        org_id: str,
        member_id: str,
        backup_id: str,
    ) -> dict[str, Any]:
        backup_id = _required("backup_id", backup_id)
        manifest = self.manifest_service.manifests.get(backup_id)
        if manifest is None or manifest.get("status") != "active":
            raise ValueError("backup_not_found")
        if manifest.get("org_id") != org_id or manifest.get("owner_member_id") != member_id:
            raise ValueError("backup_owner_mismatch")
        return manifest


def _required(field_name: str, value: Any) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{field_name}_required")
    return normalized


def _positive_int(value: Any) -> int:
    try:
        normalized = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid_retention_count") from exc
    if normalized <= 0:
        raise ValueError("invalid_retention_count")
    return normalized


def _coerce_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _timestamp(value: datetime) -> str:
    return _coerce_datetime(value).isoformat().replace("+00:00", "Z")
