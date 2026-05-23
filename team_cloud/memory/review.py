"""Memory review queue service primitives."""

from __future__ import annotations

from dataclasses import asdict, replace
from datetime import UTC, datetime
from typing import Any


class ReviewItemNotFound(KeyError):
    """Raised when a review item does not exist."""


class ReviewItemStateError(ValueError):
    """Raised when a review item cannot transition from its current state."""


class InMemoryMemoryReviewService:
    def __init__(
        self,
        *,
        review_repository: Any,
        memory_service: Any,
        audit_log: Any | None = None,
        notification_service: Any | None = None,
    ) -> None:
        self.review_repository = review_repository
        self.memory_service = memory_service
        self.audit_log = audit_log
        self.notification_service = notification_service

    def list_review_items(
        self,
        *,
        org_id: str,
        status: str = "pending",
        review_kind: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        items = []
        for item in self.review_repository.review_items.values():
            if item.org_id != org_id:
                continue
            if status and item.status != status:
                continue
            if review_kind and item.review_kind != review_kind:
                continue
            items.append(_serialize_review_item(item))
            if len(items) >= limit:
                break
        return items

    def approve_review_item(
        self,
        review_id: str,
        *,
        actor_member_id: str,
        edits: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        item = self._require_pending(review_id)
        edits = edits or {}
        update_payload = {
            "status": "active",
            "actor_member_id": actor_member_id,
        }
        for field_name in ("content", "memory_type", "sensitivity"):
            if field_name in edits:
                update_payload[field_name] = edits[field_name]
        memory = self.memory_service.update_memory(item.memory_id, update_payload)
        updated = replace(
            item,
            status="approved",
            reviewer_member_id=actor_member_id,
            reviewed_at=_now(),
        )
        self.review_repository.review_items[review_id] = updated
        self._record_audit(
            action="memory.review.approved",
            decision="approved",
            item=updated,
            actor_member_id=actor_member_id,
            metadata={
                "memory_id": item.memory_id,
                "edited": any(field in edits for field in ("content", "memory_type", "sensitivity")),
            },
        )
        return {
            "review_item": _serialize_review_item(updated),
            "memory": memory,
        }

    def notify_review_backlog(
        self,
        *,
        org_id: str,
        reviewer_member_ids: list[str] | tuple[str, ...],
        threshold_count: int,
        review_kind: str | None = None,
    ) -> dict[str, Any] | None:
        if self.notification_service is None:
            return None
        pending = self.list_review_items(
            org_id=org_id,
            status="pending",
            review_kind=review_kind,
            limit=max(int(threshold_count), 100),
        )
        if len(pending) < int(threshold_count):
            return None
        oldest_created_at = min((item["created_at"] for item in pending), default=None)
        return self.notification_service.notify_review_backlog(
            org_id=org_id,
            reviewer_member_ids=reviewer_member_ids,
            pending_count=len(pending),
            review_kind=review_kind,
            oldest_created_at=oldest_created_at,
        )

    def reject_review_item(
        self,
        review_id: str,
        *,
        actor_member_id: str,
        reason: str | None = None,
    ) -> dict[str, Any]:
        item = self._require_pending(review_id)
        memory = self.memory_service.update_memory(
            item.memory_id,
            {
                "status": "rejected",
                "actor_member_id": actor_member_id,
            },
        )
        updated = replace(
            item,
            status="rejected",
            reviewer_member_id=actor_member_id,
            reason=reason,
            reviewed_at=_now(),
        )
        self.review_repository.review_items[review_id] = updated
        self._record_audit(
            action="memory.review.rejected",
            decision="rejected",
            item=updated,
            actor_member_id=actor_member_id,
            metadata={
                "memory_id": item.memory_id,
                "reason": reason,
            },
        )
        return {
            "review_item": _serialize_review_item(updated),
            "memory": memory,
        }

    def _require_pending(self, review_id: str):
        item = self.review_repository.review_items.get(review_id)
        if item is None:
            raise ReviewItemNotFound(review_id)
        if item.status != "pending":
            raise ReviewItemStateError("review item is not pending")
        return item

    def _record_audit(
        self,
        *,
        action: str,
        decision: str,
        item: Any,
        actor_member_id: str,
        metadata: dict[str, Any],
    ) -> None:
        if self.audit_log is None:
            return
        self.audit_log.record(
            action=action,
            org_id=item.org_id,
            actor_type="human",
            actor_member_id=actor_member_id,
            resource_type="memory_review_item",
            resource_id=item.id,
            decision=decision,
            metadata=metadata,
        )


def _serialize_review_item(item: Any) -> dict[str, Any]:
    return asdict(item)


def _now() -> str:
    return datetime.now(UTC).isoformat()
