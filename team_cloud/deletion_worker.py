"""Hard delete worker contract for Team Cloud deletion requests."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Callable, Iterable

from team_cloud.authz.outbox import (
    InMemoryRelationshipOutboxRepository,
    RelationshipOutboxService,
)


RelationshipSnapshot = Callable[[dict[str, Any]], Iterable[str]]


class HardDeleteWorker:
    """Processes deletion requests handed off by DataDeletionRequestService."""

    def __init__(
        self,
        *,
        deletion_service: Any,
        audit_log: Any | None = None,
        org_service: Any | None = None,
        memory_service: Any | None = None,
        cloud_session_repository: Any | None = None,
        object_manifest_service: Any | None = None,
        relationship_outbox_repository: InMemoryRelationshipOutboxRepository | None = None,
        relationship_snapshot: RelationshipSnapshot | Iterable[str] | None = None,
        max_attempts: int = 3,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.deletion_service = deletion_service
        self.audit_log = audit_log
        self.org_service = org_service
        self.memory_service = memory_service
        self.cloud_session_repository = cloud_session_repository
        self.object_manifest_service = object_manifest_service
        self.relationship_snapshot = relationship_snapshot
        self.max_attempts = max(1, int(max_attempts))
        self._now = now or (lambda: datetime.now(UTC))
        self.relationship_outbox = (
            RelationshipOutboxService(relationship_outbox_repository)
            if relationship_outbox_repository is not None
            else None
        )

    def process_ready(self, *, limit: int = 100) -> dict[str, int]:
        summary = {"processed": 0, "completed": 0, "failed": 0, "dead_letter": 0}
        for request in self._ready_requests(limit=limit):
            summary["processed"] += 1
            try:
                self._process_request(request)
            except Exception as exc:
                dead_letter = self._record_failure(request, exc)
                summary["dead_letter" if dead_letter else "failed"] += 1
                continue
            summary["completed"] += 1
        return summary

    def _ready_requests(self, *, limit: int) -> list[dict[str, Any]]:
        candidates = [
            request
            for request in self.deletion_service.requests.values()
            if request.get("status") in {"ready_for_worker", "worker_failed"}
        ]
        candidates.sort(key=lambda item: (item.get("updated_at") or "", item["id"]))
        return candidates[:limit]

    def _process_request(self, request: dict[str, Any]) -> None:
        request["status"] = "ready_for_worker"
        request["last_error"] = None
        request.setdefault("worker_attempts", 0)
        request["updated_at"] = _timestamp(self._now())
        self._disable_access(request)
        self._soft_delete_rows(request)
        self._delete_objects(request)
        self._hard_delete_rows_after_retention(request)
        self.deletion_service.mark_completed(
            request["id"],
            completed_by_member_id="hard-delete-worker",
        )

    def _disable_access(self, request: dict[str, Any]) -> None:
        if request["target_type"] == "member" and self.org_service is not None:
            members = getattr(self.org_service, "members", {})
            if (request["org_id"], request["target_id"]) in members:
                self.org_service.disable_member(
                    org_id=request["org_id"],
                    member_id=request["target_id"],
                )

        if self.relationship_outbox is None or self.relationship_snapshot is None:
            return
        relationships = self._relationships_for(request)
        if not relationships:
            return
        self.relationship_outbox.enqueue(
            org_id=request["org_id"],
            aggregate_type=request["target_type"],
            aggregate_id=request["target_id"],
            operation="delete",
            relationships=relationships,
            idempotency_key=f"deletion-request:{request['id']}:relationships",
            created_at=self._now(),
        )

    def _soft_delete_rows(self, request: dict[str, Any]) -> None:
        if self.memory_service is not None:
            for memory_id, memory in list(getattr(self.memory_service, "items", {}).items()):
                if not _matches_target(memory, request):
                    continue
                if request["mode"] == "anonymize":
                    memory["content"] = "[ANONYMIZED]"
                    memory["normalized_content"] = "[anonymized]"
                    memory["updated_at"] = _timestamp(self._now())
                    continue
                if memory.get("status") != "deleted":
                    self.memory_service.delete_memory(
                        memory_id,
                        actor_member_id="hard-delete-worker",
                    )

        sessions = getattr(self.cloud_session_repository, "_sessions", None)
        if isinstance(sessions, dict):
            for session in sessions.values():
                if _matches_target(session, request):
                    session["status"] = "deleted"
                    session["updated_at"] = _timestamp(self._now())

    def _delete_objects(self, request: dict[str, Any]) -> None:
        manifests = getattr(self.object_manifest_service, "manifests", None)
        if not isinstance(manifests, dict):
            return
        for object_id, manifest in list(manifests.items()):
            if manifest.get("status") == "deleted":
                continue
            if not _matches_target(manifest, request):
                continue
            self.object_manifest_service.mark_deleted(
                object_id,
                deleted_at=self._now(),
            )

    def _hard_delete_rows_after_retention(self, request: dict[str, Any]) -> None:
        if request["mode"] != "hard_delete":
            return
        removed_memory_ids = self._hard_delete_memory_rows(request)
        self._hard_delete_session_rows(request)
        self._hard_delete_admin_rows(request)
        if removed_memory_ids:
            self._delete_memory_events(removed_memory_ids)

    def _hard_delete_memory_rows(self, request: dict[str, Any]) -> set[str]:
        removed_ids: set[str] = set()
        if self.memory_service is None:
            return removed_ids
        items = getattr(self.memory_service, "items", {})
        for memory_id, memory in list(items.items()):
            if _matches_target(memory, request):
                removed_ids.add(memory_id)
                del items[memory_id]
        return removed_ids

    def _hard_delete_session_rows(self, request: dict[str, Any]) -> None:
        sessions = getattr(self.cloud_session_repository, "_sessions", None)
        if not isinstance(sessions, dict):
            return
        for session_id, session in list(sessions.items()):
            if _matches_target(session, request):
                del sessions[session_id]

    def _hard_delete_admin_rows(self, request: dict[str, Any]) -> None:
        if self.org_service is None:
            return
        if request["target_type"] == "member":
            getattr(self.org_service, "members", {}).pop(
                (request["org_id"], request["target_id"]),
                None,
            )
            return
        if request["target_type"] == "org":
            org_id = request["org_id"]
            getattr(self.org_service, "organizations", {}).pop(org_id, None)
            _delete_keys_for_org(getattr(self.org_service, "members", {}), org_id)
            _delete_keys_for_org(getattr(self.org_service, "teams", {}), org_id)

    def _delete_memory_events(self, removed_memory_ids: set[str]) -> None:
        events = getattr(self.memory_service, "events", None)
        if isinstance(events, list):
            events[:] = [
                event for event in events if event.get("memory_id") not in removed_memory_ids
            ]

    def _relationships_for(self, request: dict[str, Any]) -> list[str]:
        if callable(self.relationship_snapshot):
            values = self.relationship_snapshot(request)
        else:
            values = self.relationship_snapshot or ()
        return [str(value) for value in values if str(value or "").strip()]

    def _record_failure(self, request: dict[str, Any], exc: Exception) -> bool:
        attempts = int(request.get("worker_attempts") or 0) + 1
        request["worker_attempts"] = attempts
        request["last_error"] = str(exc)
        request["updated_at"] = _timestamp(self._now())
        dead_letter = attempts >= self.max_attempts
        request["status"] = "dead_letter" if dead_letter else "worker_failed"
        self._audit(
            action=(
                "data_deletion.worker_dead_letter"
                if dead_letter
                else "data_deletion.worker_failed"
            ),
            request=request,
            decision="dead_letter" if dead_letter else "failed",
        )
        return dead_letter

    def _audit(self, *, action: str, request: dict[str, Any], decision: str) -> None:
        if self.audit_log is None:
            return
        self.audit_log.record(
            org_id=request["org_id"],
            actor_type="system",
            action=action,
            resource_type="data_deletion_request",
            resource_id=request["id"],
            decision=decision,
            metadata={
                "target_type": request["target_type"],
                "target_id": request["target_id"],
                "mode": request["mode"],
                "status": request["status"],
                "worker_attempts": request.get("worker_attempts", 0),
                "last_error": request.get("last_error"),
            },
        )


def _matches_target(record: dict[str, Any], request: dict[str, Any]) -> bool:
    org_id = request["org_id"]
    if record.get("org_id") != org_id:
        return False
    target_type = request["target_type"]
    target_id = request["target_id"]
    if target_type == "org":
        return target_id in {org_id, record.get("id"), record.get("org_id")}
    if target_type == "member":
        return target_id in {
            record.get("id"),
            record.get("member_id"),
            record.get("owner_member_id"),
            record.get("subject_member_id"),
            record.get("created_by_member_id"),
        }
    if target_type == "project":
        return target_id in {record.get("id"), record.get("project_id")}
    return False


def _delete_keys_for_org(items: dict[Any, Any], org_id: str) -> None:
    for key in list(items):
        if isinstance(key, tuple) and key and key[0] == org_id:
            del items[key]


def _timestamp(value: datetime) -> str:
    parsed = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).isoformat().replace("+00:00", "Z")
