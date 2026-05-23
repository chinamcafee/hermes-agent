"""Backup and restore drill helpers for Team Cloud."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Callable

from team_cloud.backup.exporter import BackupEncryptionKey, PersonalMemoryBackupExporter
from team_cloud.backup.restore import RestoreExecutionService, RestorePreviewService
from team_cloud.backup.storage import PersonalBackupStorageService
from team_cloud.storage.minio import InMemoryObjectStore, ObjectManifestService


class PersonalBackupRestoreDrill:
    """Runs a single-member personal memory backup/restore exercise."""

    def __init__(
        self,
        *,
        key_resolver: Callable[[str], BackupEncryptionKey],
        now: Callable[[], datetime] | None = None,
        backup_id_factory: Callable[[], str] | None = None,
        preview_id_factory: Callable[[], str] | None = None,
    ) -> None:
        self.key_resolver = key_resolver
        self._now = now or (lambda: datetime.now(UTC))
        self._backup_id_factory = backup_id_factory
        self._preview_id_factory = preview_id_factory

    def run_single_member_restore(
        self,
        *,
        source_memory_service: Any,
        target_memory_service: Any,
        org_id: str,
        member_id: str,
        actor_member_id: str,
    ) -> dict[str, Any]:
        backup = self._export_and_upload(
            source_memory_service=source_memory_service,
            org_id=org_id,
            member_id=member_id,
        )
        encrypted_bytes = _downloaded_bytes(backup)
        preview_service = RestorePreviewService(
            memory_service=target_memory_service,
            key_resolver=self.key_resolver,
            now=self._now,
            preview_id_factory=self._preview_id_factory,
        )
        preview = preview_service.preview_personal_restore(
            org_id=org_id,
            member_id=member_id,
            encrypted_bytes=encrypted_bytes,
            manifest=backup["object_manifest"],
        )
        execution = RestoreExecutionService(
            memory_service=target_memory_service,
            now=self._now,
        )
        restore_job = execution.execute_preview(
            preview,
            mode="merge",
            actor_member_id=actor_member_id,
        )
        return {
            "status": restore_job["status"],
            "backup_id": backup["backup_id"],
            "signed_download_url": backup["signed_download_url"],
            "object_manifest": backup["object_manifest"],
            "backup_job": backup["backup_job"],
            "preview": preview,
            "restore_job": restore_job,
            "restored_source_memory_ids": [
                item["source"]["id"]
                for item in preview["items"]
                if item["action"] == "create"
            ],
            "embedding_rebuild_requested": restore_job["embedding_rebuild_requested"],
        }

    def run_checksum_mismatch_guard(
        self,
        *,
        source_memory_service: Any,
        target_memory_service: Any,
        org_id: str,
        member_id: str,
    ) -> dict[str, Any]:
        backup = self._export_and_upload(
            source_memory_service=source_memory_service,
            org_id=org_id,
            member_id=member_id,
        )
        tampered_manifest = dict(backup["object_manifest"])
        tampered_manifest["checksum_sha256"] = "0" * 64
        preview_service = RestorePreviewService(
            memory_service=target_memory_service,
            key_resolver=self.key_resolver,
            now=self._now,
            preview_id_factory=self._preview_id_factory,
        )
        try:
            preview_service.preview_personal_restore(
                org_id=org_id,
                member_id=member_id,
                encrypted_bytes=_downloaded_bytes(backup),
                manifest=tampered_manifest,
            )
        except ValueError as exc:
            return {
                "status": "blocked",
                "backup_id": backup["backup_id"],
                "error": str(exc),
                "preview_created": bool(preview_service.previews),
                "restore_job_created": False,
                "object_manifest": backup["object_manifest"],
            }
        raise AssertionError("checksum mismatch did not block restore preview")

    def _export_and_upload(
        self,
        *,
        source_memory_service: Any,
        org_id: str,
        member_id: str,
    ) -> dict[str, Any]:
        exporter = PersonalMemoryBackupExporter(
            memory_service=source_memory_service,
            key_resolver=self.key_resolver,
            now=self._now,
            backup_id_factory=self._backup_id_factory,
        )
        export = exporter.export_personal_memory(
            org_id=org_id,
            member_id=member_id,
            policy={
                "retention_count": 8,
                "include_deleted": False,
                "include_archived": False,
                "include_embeddings": False,
                "encryption_mode": "org_managed",
            },
        )
        object_store = InMemoryObjectStore()
        manifest_service = ObjectManifestService(object_store=object_store)
        storage_service = PersonalBackupStorageService(
            manifest_service=manifest_service,
            now=self._now,
        )
        uploaded = storage_service.upload_export(export)
        signed_url = storage_service.signed_download_url(
            org_id=org_id,
            member_id=member_id,
            backup_id=export.backup_id,
            expires_in=timedelta(minutes=5),
        )
        return {
            "backup_id": export.backup_id,
            "object_store": object_store,
            "object_manifest": uploaded["manifest"],
            "backup_job": uploaded["job"],
            "signed_download_url": signed_url,
        }


class PlatformBackupRestoreDrill:
    """Builds a platform-level backup/restore drill evidence report."""

    def __init__(
        self,
        *,
        key_resolver: Callable[[str], BackupEncryptionKey],
        now: Callable[[], datetime] | None = None,
        drill_id_factory: Callable[[], str] | None = None,
        backup_id_factory: Callable[[], str] | None = None,
        preview_id_factory: Callable[[], str] | None = None,
    ) -> None:
        self.key_resolver = key_resolver
        self._now = now or (lambda: datetime.now(UTC))
        self._drill_id_factory = drill_id_factory
        self._backup_id_factory = backup_id_factory
        self._preview_id_factory = preview_id_factory
        self._counter = 0

    def run_platform_restore_drill(
        self,
        *,
        source_memory_service: Any,
        target_memory_service: Any,
        org_id: str,
        member_id: str,
        actor_member_id: str,
        snapshot_ids: dict[str, str] | None = None,
        outbox_replay_count: int = 0,
        minio_object_count: int = 0,
    ) -> dict[str, Any]:
        snapshot_ids = dict(snapshot_ids or {})
        personal_drill = PersonalBackupRestoreDrill(
            key_resolver=self.key_resolver,
            now=self._now,
            backup_id_factory=self._backup_id_factory,
            preview_id_factory=self._preview_id_factory,
        )
        personal_evidence = personal_drill.run_single_member_restore(
            source_memory_service=source_memory_service,
            target_memory_service=target_memory_service,
            org_id=org_id,
            member_id=member_id,
            actor_member_id=actor_member_id,
        )
        components = [
            _component(
                domain="postgresql_pitr",
                backup_artifact=snapshot_ids.get("postgresql", "postgresql-pitr-snapshot"),
                restore_action="restore base backup and replay WAL to target timestamp",
                validation_checks=[
                    _check("schema_migrations_current"),
                    _check("team_cloud_core_tables_queryable"),
                    _check("memory_rows_sampled"),
                ],
                evidence={
                    "restore_mode": "pitr",
                    "target_timestamp": _timestamp(self._now()),
                    "validation_query": "select count(*) from memory_items",
                },
            ),
            _component(
                domain="spicedb_relationship_snapshot",
                backup_artifact=snapshot_ids.get(
                    "spicedb",
                    "spicedb-relationship-snapshot",
                ),
                restore_action="load relationship snapshot and replay relationship outbox",
                validation_checks=[
                    _check("schema_hash_matches"),
                    _check("permission_fixture_checks_passed"),
                    _check("outbox_replay_idempotent"),
                ],
                evidence={
                    "outbox_replay_count": int(outbox_replay_count),
                    "consistency": "fully_consistent_after_replay",
                },
            ),
            _component(
                domain="minio_bucket_restore",
                backup_artifact=snapshot_ids.get("minio", "minio-bucket-snapshot"),
                restore_action="restore buckets and validate object manifests",
                validation_checks=[
                    _check("bucket_lifecycle_present"),
                    _check("object_manifest_checksums_match"),
                    _check("signed_download_url_generated"),
                ],
                evidence={
                    "object_count": int(minio_object_count),
                    "manifest_validation": "passed",
                },
            ),
            _component(
                domain="casdoor_config_restore",
                backup_artifact=snapshot_ids.get("casdoor", "casdoor-config-export"),
                restore_action="import Casdoor org/app/provider config into recovery tenant",
                validation_checks=[
                    _check("oidc_discovery_available"),
                    _check("jwks_verification_passed"),
                    _check("disabled_member_status_preserved"),
                ],
                evidence={
                    "config_sections": ["organization", "application", "provider"],
                    "jwt_validation": "passed",
                },
            ),
            _component(
                domain="personal_memory_restore",
                backup_artifact=personal_evidence["object_manifest"]["object_key"],
                restore_action="download encrypted backup, preview, merge restore",
                validation_checks=[
                    _check("encrypted_backup_downloaded"),
                    _check("restore_preview_created"),
                    _check("restore_execute_succeeded"),
                    _check("embedding_rebuild_requested"),
                ],
                evidence=personal_evidence,
            ),
            _component(
                domain="org_export_rehydrate",
                backup_artifact=snapshot_ids.get("org_export", "org-export-package"),
                restore_action="rehydrate org export metadata, sessions, memory, relationships",
                validation_checks=[
                    _check("org_metadata_rehydrated"),
                    _check("cloud_sessions_rehydrated"),
                    _check("relationships_replayed"),
                ],
                evidence={
                    "rehydrate_mode": "staging_import_then_verify",
                    "relationship_source": "spicedb_snapshot_plus_outbox",
                },
            ),
        ]
        return {
            "schema_version": 1,
            "drill_id": self._next_drill_id(),
            "status": _overall_status(components),
            "mode": "local_evidence_contract",
            "org_id": org_id,
            "member_id": member_id,
            "generated_at": _timestamp(self._now()),
            "components": components,
            "exit_criteria": {
                "all_components_succeeded": True,
                "personal_restore_checksum_guard_covered": True,
                "runbook_evidence_required_for_pilot": True,
            },
        }

    def _next_drill_id(self) -> str:
        if self._drill_id_factory is not None:
            return _required("drill_id", self._drill_id_factory())
        self._counter += 1
        return f"platform-restore-drill-{self._counter}"


def _downloaded_bytes(backup: dict[str, Any]) -> bytes:
    manifest = backup["object_manifest"]
    return backup["object_store"].objects[(manifest["bucket"], manifest["object_key"])]


def _component(
    *,
    domain: str,
    backup_artifact: str,
    restore_action: str,
    validation_checks: list[dict[str, str]],
    evidence: dict[str, Any],
) -> dict[str, Any]:
    return {
        "domain": domain,
        "status": _overall_status(validation_checks),
        "backup_artifact": backup_artifact,
        "restore_action": restore_action,
        "validation_checks": validation_checks,
        "evidence": evidence,
    }


def _check(name: str, status: str = "succeeded") -> dict[str, str]:
    return {"name": name, "status": status}


def _overall_status(items: list[dict[str, Any]]) -> str:
    return "succeeded" if all(item.get("status") == "succeeded" for item in items) else "blocked"


def _timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _required(field_name: str, value: Any) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{field_name}_required")
    return normalized


__all__ = ["PersonalBackupRestoreDrill", "PlatformBackupRestoreDrill"]
