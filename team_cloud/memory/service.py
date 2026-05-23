"""In-memory Memory CRUD service."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
import hashlib
from typing import Any


class MemoryNotFound(KeyError):
    """Raised when a memory item does not exist."""


@dataclass
class InMemoryMemoryService:
    relationship_service: Any | None = None
    items: dict[str, dict[str, Any]] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)
    _counter: int = 0

    def create_memory(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._counter += 1
        scope = payload["scope"]
        content = payload["content"]
        status = payload.get("status") or (
            "pending_review" if scope == "team_shared" else "active"
        )
        memory = {
            "id": f"mem-{self._counter}",
            "org_id": payload["org_id"],
            "scope": scope,
            "subject_member_id": payload.get("subject_member_id"),
            "team_id": payload.get("team_id"),
            "project_id": payload.get("project_id"),
            "status": status,
            "sensitivity": payload.get("sensitivity", "normal"),
            "memory_type": payload.get("memory_type", "fact"),
            "content": content,
            "normalized_content": _normalize(content),
            "source_type": payload.get("source_type", "conversation"),
            "source_ref": payload.get("source_ref", {}),
            "version": 1,
            "checksum_sha256": _checksum(content),
            "created_by_member_id": payload.get("created_by_member_id"),
            "created_at": _now(),
            "updated_at": _now(),
            "deleted_at": None,
        }
        _validate_scope(memory)
        self.items[memory["id"]] = memory
        self._record_event(memory=memory, event_type="create")
        if self.relationship_service is not None:
            self.relationship_service.enqueue_memory_relationships(
                memory,
                reviewer_member_ids=_reviewer_member_ids(payload),
            )
        return dict(memory)

    def list_memory(
        self,
        *,
        org_id: str,
        scope: str | None = None,
        status: str | None = None,
        memory_type: str | None = None,
        sensitivity: str | None = None,
    ) -> list[dict[str, Any]]:
        results = []
        for memory in self.items.values():
            if memory["org_id"] != org_id:
                continue
            if scope and memory["scope"] != scope:
                continue
            if status and memory["status"] != status:
                continue
            if memory_type and memory["memory_type"] != memory_type:
                continue
            if sensitivity and memory["sensitivity"] != sensitivity:
                continue
            results.append(dict(memory))
        return results

    def update_memory(self, memory_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        memory = self._require(memory_id)
        if "content" in payload:
            content = payload["content"]
            memory["content"] = content
            memory["normalized_content"] = _normalize(content)
            memory["checksum_sha256"] = _checksum(content)
        for field_name in ("memory_type", "sensitivity", "status"):
            if field_name in payload:
                memory[field_name] = payload[field_name]
        memory["version"] += 1
        memory["updated_at"] = _now()
        self._record_event(
            memory=memory,
            event_type="update",
            actor_member_id=payload.get("actor_member_id"),
        )
        return dict(memory)

    def archive_memory(self, memory_id: str, *, actor_member_id: str | None = None) -> dict[str, Any]:
        memory = self._require(memory_id)
        memory["status"] = "archived"
        memory["updated_at"] = _now()
        self._record_event(memory=memory, event_type="archive", actor_member_id=actor_member_id)
        return dict(memory)

    def delete_memory(self, memory_id: str, *, actor_member_id: str | None = None) -> dict[str, Any]:
        memory = self._require(memory_id)
        memory["status"] = "deleted"
        memory["deleted_at"] = _now()
        memory["updated_at"] = _now()
        self._record_event(memory=memory, event_type="delete", actor_member_id=actor_member_id)
        return dict(memory)

    def restore_memory(self, memory_id: str, *, actor_member_id: str | None = None) -> dict[str, Any]:
        memory = self._require(memory_id)
        memory["status"] = "active"
        memory["deleted_at"] = None
        memory["updated_at"] = _now()
        self._record_event(memory=memory, event_type="restore", actor_member_id=actor_member_id)
        return dict(memory)

    def _require(self, memory_id: str) -> dict[str, Any]:
        if memory_id not in self.items:
            raise MemoryNotFound(memory_id)
        return self.items[memory_id]

    def _record_event(
        self,
        *,
        memory: dict[str, Any],
        event_type: str,
        actor_member_id: str | None = None,
    ) -> None:
        self.events.append(
            {
                "org_id": memory["org_id"],
                "memory_id": memory["id"],
                "actor_member_id": actor_member_id,
                "event_type": event_type,
                "event_data": {"version": memory["version"]},
                "created_at": _now(),
            }
        )


def _validate_scope(memory: dict[str, Any]) -> None:
    if memory["scope"] == "personal":
        if not memory["subject_member_id"] or memory["team_id"]:
            raise ValueError("personal memory requires subject_member_id and no team_id")
        return
    if memory["scope"] == "team_shared":
        if memory["subject_member_id"] or not memory["team_id"]:
            raise ValueError("team_shared memory requires team_id and no subject_member_id")
        return
    raise ValueError("scope must be personal or team_shared")


def _reviewer_member_ids(payload: dict[str, Any]) -> tuple[str, ...]:
    reviewers: list[str] = []
    for field_name in ("reviewer_member_id", "curator_member_id"):
        if payload.get(field_name):
            reviewers.append(str(payload[field_name]))
    for field_name in ("reviewer_member_ids", "curator_member_ids"):
        values = payload.get(field_name) or ()
        if isinstance(values, str):
            reviewers.append(values)
            continue
        reviewers.extend(str(value) for value in values if value)
    return tuple(reviewers)


def _normalize(content: str) -> str:
    return " ".join(content.casefold().split())


def _checksum(content: str) -> str:
    return hashlib.sha256(_normalize(content).encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(UTC).isoformat()
