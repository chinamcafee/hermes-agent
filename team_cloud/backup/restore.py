"""Restore preview generation for encrypted personal memory backups."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from io import BytesIO
import hashlib
import json
from typing import Any, Callable
from zipfile import ZipFile

from team_cloud.backup.exporter import BackupEncryptionKey, decrypt_backup_package


class RestorePreviewService:
    """Builds restore previews without mutating memory state."""

    def __init__(
        self,
        *,
        memory_service: Any,
        key_resolver: Callable[[str], BackupEncryptionKey] | None = None,
        now: Callable[[], datetime] | None = None,
        preview_id_factory: Callable[[], str] | None = None,
    ) -> None:
        self.memory_service = memory_service
        self.key_resolver = key_resolver
        self._now = now or (lambda: datetime.now(UTC))
        self._preview_id_factory = preview_id_factory or _random_preview_id
        self.previews: dict[str, dict[str, Any]] = {}

    def preview_personal_restore(
        self,
        *,
        org_id: str,
        member_id: str,
        encrypted_bytes: bytes,
        manifest: dict[str, Any],
        passphrase: str | None = None,
    ) -> dict[str, Any]:
        org_id = _required("org_id", org_id)
        member_id = _required("member_id", member_id)
        if manifest.get("org_id") != org_id or manifest.get("owner_member_id") != member_id:
            raise ValueError("backup_owner_mismatch")
        plaintext_zip = decrypt_backup_package(
            encrypted_bytes,
            manifest=manifest,
            key_resolver=self.key_resolver,
            passphrase=passphrase,
        )
        source_memories = _read_backup_memories(plaintext_zip)
        current_memories = _current_personal_memories(
            self.memory_service,
            org_id=org_id,
            member_id=member_id,
        )
        items = [
            _preview_item(source=source, current_memories=current_memories)
            for source in source_memories
        ]
        preview_id = _required("preview_id", self._preview_id_factory())
        preview = {
            "id": preview_id,
            "org_id": org_id,
            "member_id": member_id,
            "backup_id": manifest["object_id"],
            "status": "previewed",
            "summary": _summary(items),
            "items": items,
            "created_at": _timestamp(self._now()),
        }
        self.previews[preview_id] = deepcopy(preview)
        return deepcopy(preview)


class RestoreExecutionService:
    """Executes a restore preview against the memory service."""

    VALID_MODES = {"merge", "overwrite", "archive_current_then_restore"}

    def __init__(
        self,
        *,
        memory_service: Any,
        now: Callable[[], datetime] | None = None,
        job_id_factory: Callable[[], str] | None = None,
    ) -> None:
        self.memory_service = memory_service
        self._now = now or (lambda: datetime.now(UTC))
        self._job_id_factory = job_id_factory
        self._job_counter = 0
        self.jobs: dict[str, dict[str, Any]] = {}
        self.embedding_rebuild_queue: list[str] = []

    def execute_preview(
        self,
        preview: dict[str, Any],
        *,
        mode: str,
        actor_member_id: str,
    ) -> dict[str, Any]:
        if mode not in self.VALID_MODES:
            raise ValueError("invalid_restore_mode")
        if preview.get("status") != "previewed":
            raise ValueError("invalid_preview_status")
        actor_member_id = _required("actor_member_id", actor_member_id)
        summary = {
            "created": 0,
            "updated": 0,
            "archived": 0,
            "skipped": 0,
            "conflicts": 0,
        }
        restored_memory_ids: list[str] = []
        for item in preview.get("items", []):
            action = item["action"]
            if action == "skip":
                summary["skipped"] += 1
                continue
            if action == "create":
                created = self._create_from_source(
                    item["source"],
                    actor_member_id=actor_member_id,
                    backup_id=str(preview["backup_id"]),
                )
                summary["created"] += 1
                restored_memory_ids.append(created["id"])
                self.embedding_rebuild_queue.append(created["id"])
                continue
            if action == "conflict":
                self._execute_conflict(
                    item,
                    mode=mode,
                    actor_member_id=actor_member_id,
                    backup_id=str(preview["backup_id"]),
                    summary=summary,
                    restored_memory_ids=restored_memory_ids,
                )
                continue
            summary["conflicts"] += 1

        status = "succeeded" if summary["conflicts"] == 0 else "blocked"
        job = {
            "id": self._next_job_id(),
            "preview_id": preview["id"],
            "backup_id": preview["backup_id"],
            "org_id": preview["org_id"],
            "member_id": preview["member_id"],
            "mode": mode,
            "status": status,
            "summary": summary,
            "restored_memory_ids": restored_memory_ids,
            "embedding_rebuild_requested": list(restored_memory_ids),
            "actor_member_id": actor_member_id,
            "created_at": _timestamp(self._now()),
            "finished_at": _timestamp(self._now()),
        }
        self.jobs[job["id"]] = deepcopy(job)
        return deepcopy(job)

    def _execute_conflict(
        self,
        item: dict[str, Any],
        *,
        mode: str,
        actor_member_id: str,
        backup_id: str,
        summary: dict[str, int],
        restored_memory_ids: list[str],
    ) -> None:
        current_memory_id = item.get("current_memory_id")
        if mode == "merge":
            summary["conflicts"] += 1
            return
        if not current_memory_id:
            summary["conflicts"] += 1
            return
        if mode == "overwrite":
            updated = self.memory_service.update_memory(
                str(current_memory_id),
                _update_payload(item["source"], actor_member_id=actor_member_id),
            )
            summary["updated"] += 1
            restored_memory_ids.append(updated["id"])
            self.embedding_rebuild_queue.append(updated["id"])
            return
        if mode == "archive_current_then_restore":
            self.memory_service.archive_memory(
                str(current_memory_id),
                actor_member_id=actor_member_id,
            )
            summary["archived"] += 1
            created = self._create_from_source(
                item["source"],
                actor_member_id=actor_member_id,
                backup_id=backup_id,
            )
            summary["created"] += 1
            restored_memory_ids.append(created["id"])
            self.embedding_rebuild_queue.append(created["id"])
            return
        raise ValueError("invalid_restore_mode")

    def _create_from_source(
        self,
        source: dict[str, Any],
        *,
        actor_member_id: str,
        backup_id: str,
    ) -> dict[str, Any]:
        payload = {
            "org_id": source["org_id"],
            "scope": "personal",
            "subject_member_id": source["subject_member_id"],
            "content": source["content"],
            "status": "active",
            "memory_type": source.get("memory_type", "fact"),
            "sensitivity": source.get("sensitivity", "normal"),
            "source_type": "restore",
            "source_ref": {
                **dict(source.get("source_ref") or {}),
                "backup_id": backup_id,
                "source_memory_id": source.get("id"),
            },
            "created_by_member_id": actor_member_id,
        }
        return self.memory_service.create_memory(payload)

    def _next_job_id(self) -> str:
        if self._job_id_factory is not None:
            return _required("restore_job_id", self._job_id_factory())
        self._job_counter += 1
        return f"restore-job-{self._job_counter}"


def _read_backup_memories(plaintext_zip: bytes) -> list[dict[str, Any]]:
    with ZipFile(BytesIO(plaintext_zip)) as archive:
        payload = archive.read("memories.jsonl").decode("utf-8")
    records = []
    for line in payload.splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def _current_personal_memories(
    memory_service: Any,
    *,
    org_id: str,
    member_id: str,
) -> list[dict[str, Any]]:
    records = []
    for memory in memory_service.list_memory(org_id=org_id, scope="personal"):
        if str(memory.get("subject_member_id") or "") != member_id:
            continue
        records.append(deepcopy(memory))
    return records


def _preview_item(
    *,
    source: dict[str, Any],
    current_memories: list[dict[str, Any]],
) -> dict[str, Any]:
    source_checksum = source.get("checksum_sha256") or _checksum(source.get("content", ""))
    source_normalized = source.get("normalized_content") or _normalize(source.get("content", ""))

    deleted_same_content = _find_current(
        current_memories,
        normalized_content=source_normalized,
        status="deleted",
    )
    if deleted_same_content is not None:
        return _item(
            source=source,
            action="conflict",
            reason="current_deleted",
            current=deleted_same_content,
            default_strategy="ask_user",
        )

    checksum_match = _find_current(
        current_memories,
        checksum_sha256=source_checksum,
        exclude_status="deleted",
    )
    if checksum_match is not None:
        return _item(
            source=source,
            action="skip",
            reason="checksum_match",
            current=checksum_match,
        )

    normalized_match = _find_current(
        current_memories,
        normalized_content=source_normalized,
        exclude_status="deleted",
    )
    if normalized_match is not None:
        if int(normalized_match.get("version", 1)) >= int(source.get("version", 1)):
            return _item(
                source=source,
                action="skip",
                reason="keep_newer",
                current=normalized_match,
            )
        return _item(
            source=source,
            action="conflict",
            reason="backup_newer",
            current=normalized_match,
            default_strategy="review",
        )

    return _item(source=source, action="create", reason="new_memory")


def _find_current(
    current_memories: list[dict[str, Any]],
    *,
    checksum_sha256: str | None = None,
    normalized_content: str | None = None,
    status: str | None = None,
    exclude_status: str | None = None,
) -> dict[str, Any] | None:
    for memory in current_memories:
        if status is not None and memory.get("status") != status:
            continue
        if exclude_status is not None and memory.get("status") == exclude_status:
            continue
        if checksum_sha256 is not None and memory.get("checksum_sha256") != checksum_sha256:
            continue
        if (
            normalized_content is not None
            and memory.get("normalized_content") != normalized_content
        ):
            continue
        return memory
    return None


def _item(
    *,
    source: dict[str, Any],
    action: str,
    reason: str,
    current: dict[str, Any] | None = None,
    default_strategy: str | None = None,
) -> dict[str, Any]:
    return {
        "source_memory_id": source.get("id"),
        "current_memory_id": current.get("id") if current else None,
        "action": action,
        "reason": reason,
        "default_strategy": default_strategy,
        "source": deepcopy(source),
        "current": deepcopy(current) if current else None,
    }


def _summary(items: list[dict[str, Any]]) -> dict[str, int]:
    summary = {"total": len(items), "create": 0, "skip": 0, "conflict": 0, "overwrite": 0}
    for item in items:
        summary[item["action"]] += 1
    return summary


def _normalize(content: str) -> str:
    return " ".join(str(content or "").casefold().split())


def _checksum(content: str) -> str:
    return hashlib.sha256(_normalize(content).encode("utf-8")).hexdigest()


def _update_payload(source: dict[str, Any], *, actor_member_id: str) -> dict[str, Any]:
    return {
        "content": source["content"],
        "memory_type": source.get("memory_type", "fact"),
        "sensitivity": source.get("sensitivity", "normal"),
        "status": "active",
        "actor_member_id": actor_member_id,
    }


def _required(field_name: str, value: Any) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{field_name}_required")
    return normalized


def _timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _random_preview_id() -> str:
    return f"restore-preview-{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}"
