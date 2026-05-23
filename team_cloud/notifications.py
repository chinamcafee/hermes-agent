"""Team Cloud notification event primitives."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any, Callable, Iterable
from uuid import uuid4


class NotificationNotFound(KeyError):
    """Raised when a notification does not exist."""


class InMemoryNotificationService:
    """Small notification event queue for GA governance workflows."""

    def __init__(
        self,
        *,
        now: Callable[[], datetime] | None = None,
        notification_id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._now = now or (lambda: datetime.now(UTC))
        self._notification_id_factory = notification_id_factory or _random_notification_id
        self.notifications: dict[str, dict[str, Any]] = {}
        self._ids_by_dedupe_key: dict[str, str] = {}

    def create_notification(
        self,
        *,
        org_id: str,
        notification_type: str,
        severity: str,
        recipient_member_ids: Iterable[str],
        channels: Iterable[str] | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        payload: dict[str, Any] | None = None,
        dedupe_key: str | None = None,
    ) -> dict[str, Any]:
        if dedupe_key:
            existing_id = self._ids_by_dedupe_key.get(dedupe_key)
            if existing_id is not None:
                return deepcopy(self.notifications[existing_id])
        notification_id = _required("notification_id", self._notification_id_factory())
        notification = {
            "id": notification_id,
            "org_id": _required("org_id", org_id),
            "type": _required("notification_type", notification_type),
            "severity": _required("severity", severity),
            "recipient_member_ids": _normalize_list("recipient_member_ids", recipient_member_ids),
            "channels": _normalize_list("channels", channels or ("in_app",)),
            "resource_type": resource_type,
            "resource_id": resource_id,
            "payload": deepcopy(payload or {}),
            "status": "unread",
            "created_at": _timestamp(self._now()),
            "acknowledged_by": None,
            "acknowledged_at": None,
            "dedupe_key": dedupe_key,
        }
        self.notifications[notification_id] = notification
        if dedupe_key:
            self._ids_by_dedupe_key[dedupe_key] = notification_id
        return deepcopy(notification)

    def notify_backup_failure(
        self,
        *,
        org_id: str,
        member_id: str,
        backup_id: str,
        policy_id: str | None,
        error: str,
        channels: Iterable[str] | None = None,
    ) -> dict[str, Any]:
        return self.create_notification(
            org_id=org_id,
            notification_type="backup_failure",
            severity="warning",
            recipient_member_ids=[member_id],
            channels=channels or ("in_app",),
            resource_type="personal_backup",
            resource_id=backup_id,
            payload={
                "backup_id": backup_id,
                "policy_id": policy_id,
                "error": error,
            },
            dedupe_key=f"backup_failure:{org_id}:{member_id}:{backup_id}:{policy_id}:{error}",
        )

    def notify_break_glass_accessed(
        self,
        *,
        org_id: str,
        target_member_id: str,
        request_id: str,
        resource_type: str,
        resource_id: str,
        requester_member_id: str,
    ) -> dict[str, Any]:
        return self.create_notification(
            org_id=org_id,
            notification_type="break_glass_accessed",
            severity="critical",
            recipient_member_ids=[target_member_id],
            channels=("in_app",),
            resource_type=resource_type,
            resource_id=resource_id,
            payload={
                "request_id": request_id,
                "requester_member_id": requester_member_id,
            },
            dedupe_key=f"break_glass_accessed:{org_id}:{target_member_id}:{request_id}",
        )

    def notify_review_backlog(
        self,
        *,
        org_id: str,
        reviewer_member_ids: Iterable[str],
        pending_count: int,
        review_kind: str | None = None,
        oldest_created_at: str | None = None,
    ) -> dict[str, Any]:
        normalized_kind = str(review_kind or "all").strip()
        return self.create_notification(
            org_id=org_id,
            notification_type="review_backlog",
            severity="warning",
            recipient_member_ids=reviewer_member_ids,
            channels=("in_app",),
            resource_type="memory_review_queue",
            resource_id=normalized_kind,
            payload={
                "pending_count": pending_count,
                "review_kind": review_kind,
                "oldest_created_at": oldest_created_at,
            },
            dedupe_key=f"review_backlog:{org_id}:{normalized_kind}:{pending_count}",
        )

    def list_notifications(
        self,
        *,
        org_id: str,
        recipient_member_id: str | None = None,
        status: str | None = None,
        notification_type: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        items = []
        for notification in self.notifications.values():
            if notification["org_id"] != org_id:
                continue
            if recipient_member_id and recipient_member_id not in notification["recipient_member_ids"]:
                continue
            if status and notification["status"] != status:
                continue
            if notification_type and notification["type"] != notification_type:
                continue
            items.append(deepcopy(notification))
            if len(items) >= limit:
                break
        return items

    def acknowledge(self, notification_id: str, *, actor_member_id: str) -> dict[str, Any]:
        notification = self.notifications.get(notification_id)
        if notification is None:
            raise NotificationNotFound(notification_id)
        notification["status"] = "acknowledged"
        notification["acknowledged_by"] = _required("actor_member_id", actor_member_id)
        notification["acknowledged_at"] = _timestamp(self._now())
        return deepcopy(notification)


def _normalize_list(field_name: str, values: Iterable[str]) -> list[str]:
    normalized = [str(value).strip() for value in values if str(value).strip()]
    if not normalized:
        raise ValueError(f"{field_name}_required")
    return normalized


def _required(field_name: str, value: Any) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{field_name}_required")
    return normalized


def _timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _random_notification_id() -> str:
    return f"notification_{uuid4().hex}"
