"""Break-glass workflow primitives for sensitive personal data access."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
import secrets
from typing import Any, Callable

from team_cloud.authz.outbox import (
    InMemoryRelationshipOutboxRepository,
    RelationshipOutboxService,
)


REQUESTER_ROLES = {"owner", "security_admin"}
APPROVER_BY_REQUESTER_ROLE = {
    "owner": "security_admin",
    "security_admin": "owner",
}
RESOURCE_TYPES = {"memory", "backup"}


class BreakGlassService:
    """Coordinates two-person break-glass access windows."""

    def __init__(
        self,
        *,
        audit_log: Any | None = None,
        relationship_outbox_repository: InMemoryRelationshipOutboxRepository | None = None,
        notification_service: Any | None = None,
        now: Callable[[], datetime] | None = None,
        request_id_factory: Callable[[], str] | None = None,
    ) -> None:
        self.audit_log = audit_log
        self.notification_service = notification_service
        self.relationship_outbox = (
            RelationshipOutboxService(relationship_outbox_repository)
            if relationship_outbox_repository is not None
            else None
        )
        self._now = now or (lambda: datetime.now(UTC))
        self._request_id_factory = request_id_factory or _random_request_id
        self.requests: dict[str, dict[str, Any]] = {}
        self.notifications: list[dict[str, Any]] = []

    def create_request(
        self,
        *,
        org_id: str,
        requester_member_id: str,
        requester_role: str,
        target_member_id: str,
        resource_type: str,
        resource_id: str,
        permission: str,
        reason: str,
        ticket_id: str,
        starts_at: datetime | str,
        expires_at: datetime | str,
        delayed_notification: bool = False,
    ) -> dict[str, Any]:
        requester_role = _validate_requester_role(requester_role)
        resource_type = _validate_resource_type(resource_type)
        starts_at_value = _coerce_datetime(starts_at)
        expires_at_value = _coerce_datetime(expires_at)
        if expires_at_value <= starts_at_value:
            raise ValueError("invalid_break_glass_window")
        request_id = _required("break_glass_request_id", self._request_id_factory())
        request = {
            "id": request_id,
            "org_id": _required("org_id", org_id),
            "requester_member_id": _required("requester_member_id", requester_member_id),
            "requester_role": requester_role,
            "required_approver_role": APPROVER_BY_REQUESTER_ROLE[requester_role],
            "target_member_id": _required("target_member_id", target_member_id),
            "resource_type": resource_type,
            "resource_id": _required("resource_id", resource_id),
            "permission": _required("permission", permission),
            "reason": _required("reason", reason),
            "ticket_id": _required("ticket_id", ticket_id),
            "starts_at": _timestamp(starts_at_value),
            "expires_at": _timestamp(expires_at_value),
            "delayed_notification": bool(delayed_notification),
            "approval_status": "pending",
            "status": "pending_approval",
            "approver_member_id": None,
            "approved_at": None,
            "expired_at": None,
            "created_at": _timestamp(self._now()),
            "updated_at": _timestamp(self._now()),
        }
        self.requests[request_id] = request
        self._audit(action="break_glass.requested", request=request, decision="requested")
        return deepcopy(request)

    def approve_request(
        self,
        request_id: str,
        *,
        approver_member_id: str,
        approver_role: str,
    ) -> dict[str, Any]:
        request = self._require(request_id)
        if request["approval_status"] != "pending":
            raise ValueError("invalid_break_glass_status")
        approver_member_id = _required("approver_member_id", approver_member_id)
        if approver_member_id == request["requester_member_id"]:
            raise ValueError("break_glass_requires_different_approver")
        if str(approver_role or "").strip() != request["required_approver_role"]:
            raise ValueError("invalid_break_glass_approver_role")
        now = self._now()
        request["approval_status"] = "approved"
        request["approver_member_id"] = approver_member_id
        request["approved_at"] = _timestamp(now)
        request["status"] = "active" if _is_active_window(request, now) else "scheduled"
        request["updated_at"] = _timestamp(now)
        self._write_relationship(request, operation="create")
        self._audit(action="break_glass.approved", request=request, decision="approved")
        return deepcopy(request)

    def record_access(
        self,
        request_id: str,
        *,
        actor_member_id: str,
        at: datetime | str | None = None,
    ) -> dict[str, Any]:
        request = self._require(request_id)
        access_time = _coerce_datetime(at or self._now())
        if actor_member_id != request["requester_member_id"]:
            raise ValueError("break_glass_actor_mismatch")
        if request["approval_status"] != "approved" or not _is_active_window(request, access_time):
            raise ValueError("break_glass_not_active")
        request["status"] = "active"
        request["updated_at"] = _timestamp(access_time)
        event = self._audit(
            action="break_glass.accessed",
            request=request,
            decision="allowed",
        )
        if not request["delayed_notification"]:
            self.notifications.append(
                {
                    "org_id": request["org_id"],
                    "recipient_member_id": request["target_member_id"],
                    "type": "break_glass_accessed",
                    "request_id": request["id"],
                    "resource_type": request["resource_type"],
                    "resource_id": request["resource_id"],
                }
            )
            if self.notification_service is not None:
                self.notification_service.notify_break_glass_accessed(
                    org_id=request["org_id"],
                    target_member_id=request["target_member_id"],
                    request_id=request["id"],
                    resource_type=request["resource_type"],
                    resource_id=request["resource_id"],
                    requester_member_id=request["requester_member_id"],
                )
        return event

    def expire_requests(self, *, at: datetime | str | None = None) -> list[dict[str, Any]]:
        cutoff = _coerce_datetime(at or self._now())
        expired: list[dict[str, Any]] = []
        for request in self.requests.values():
            if request["approval_status"] != "approved":
                continue
            if request["status"] not in {"active", "scheduled"}:
                continue
            if _coerce_datetime(request["expires_at"]) > cutoff:
                continue
            request["status"] = "expired"
            request["expired_at"] = _timestamp(cutoff)
            request["updated_at"] = _timestamp(cutoff)
            self._write_relationship(request, operation="delete")
            self._audit(action="break_glass.expired", request=request, decision="expired")
            expired.append(request)
        return expired

    def _require(self, request_id: str) -> dict[str, Any]:
        normalized = _required("break_glass_request_id", request_id)
        request = self.requests.get(normalized)
        if request is None:
            raise KeyError(normalized)
        return request

    def _write_relationship(self, request: dict[str, Any], *, operation: str) -> None:
        if self.relationship_outbox is None:
            return
        self.relationship_outbox.enqueue(
            org_id=request["org_id"],
            aggregate_type="break_glass",
            aggregate_id=request["id"],
            operation=operation,
            relationships=[_relationship(request)],
            idempotency_key=f"break-glass:{request['id']}:{operation}",
            created_at=self._now(),
        )

    def _audit(
        self,
        *,
        action: str,
        request: dict[str, Any],
        decision: str,
    ) -> dict[str, Any]:
        if self.audit_log is None:
            return {}
        return self.audit_log.record(
            org_id=request["org_id"],
            actor_member_id=request["requester_member_id"],
            actor_type="member",
            action=action,
            resource_type="break_glass_request",
            resource_id=request["id"],
            decision=decision,
            metadata={
                "target_member_id": request["target_member_id"],
                "resource_type": request["resource_type"],
                "resource_id": request["resource_id"],
                "permission": request["permission"],
                "ticket_id": request["ticket_id"],
                "starts_at": request["starts_at"],
                "expires_at": request["expires_at"],
                "status": request["status"],
                "approval_status": request["approval_status"],
                "delayed_notification": request["delayed_notification"],
            },
        )


def _relationship(request: dict[str, Any]) -> str:
    return (
        f"{request['resource_type']}:{request['resource_id']}"
        f"#approved_break_glass_reader@user:{request['requester_member_id']}"
    )


def _validate_requester_role(value: str) -> str:
    normalized = str(value or "").strip()
    if normalized not in REQUESTER_ROLES:
        raise ValueError("invalid_break_glass_requester_role")
    return normalized


def _validate_resource_type(value: str) -> str:
    normalized = str(value or "").strip()
    if normalized not in RESOURCE_TYPES:
        raise ValueError("invalid_break_glass_resource_type")
    return normalized


def _is_active_window(request: dict[str, Any], at: datetime) -> bool:
    return _coerce_datetime(request["starts_at"]) <= at < _coerce_datetime(request["expires_at"])


def _required(field_name: str, value: Any) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{field_name}_required")
    return normalized


def _coerce_datetime(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _timestamp(value: datetime) -> str:
    return _coerce_datetime(value).isoformat().replace("+00:00", "Z")


def _random_request_id() -> str:
    return f"break-glass-{secrets.token_hex(16)}"
