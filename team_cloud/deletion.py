"""Data deletion request governance primitives."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
import secrets
from typing import Any, Callable


VALID_TARGET_TYPES = {"member", "project", "org"}
VALID_DELETION_MODES = {"anonymize", "soft_delete", "hard_delete"}


class DataDeletionRequestService:
    """Tracks deletion requests through approval and scheduled worker handoff."""

    def __init__(
        self,
        *,
        audit_log: Any | None = None,
        now: Callable[[], datetime] | None = None,
        request_id_factory: Callable[[], str] | None = None,
    ) -> None:
        self.audit_log = audit_log
        self._now = now or (lambda: datetime.now(UTC))
        self._request_id_factory = request_id_factory or _random_request_id
        self.requests: dict[str, dict[str, Any]] = {}

    def create_request(
        self,
        *,
        org_id: str,
        requester_member_id: str,
        target_type: str,
        target_id: str,
        mode: str,
        export_before_delete: bool = False,
        export_id: str | None = None,
        reason: str | None = None,
    ) -> dict[str, Any]:
        org_id = _required("org_id", org_id)
        requester_member_id = _required("requester_member_id", requester_member_id)
        target_type = _validate_target_type(target_type)
        mode = _validate_mode(mode)
        request_id = _required("deletion_request_id", self._request_id_factory())
        now = _timestamp(self._now())
        request = {
            "id": request_id,
            "org_id": org_id,
            "requester_member_id": requester_member_id,
            "target_type": target_type,
            "target_id": _required("target_id", target_id),
            "mode": mode,
            "export_before_delete": bool(export_before_delete),
            "export_id": export_id,
            "reason": reason,
            "approval_status": "pending",
            "status": "pending_approval",
            "approver_member_id": None,
            "scheduled_at": None,
            "completed_at": None,
            "execution_plan": [],
            "created_at": now,
            "updated_at": now,
        }
        self.requests[request_id] = request
        self._audit(
            action="data_deletion.requested",
            request=request,
            actor_member_id=requester_member_id,
            decision="requested",
        )
        return deepcopy(request)

    def approve_request(
        self,
        request_id: str,
        *,
        approver_member_id: str,
        scheduled_at: datetime | str | None = None,
    ) -> dict[str, Any]:
        request = self._require(request_id)
        if request["approval_status"] != "pending":
            raise ValueError("invalid_approval_status")
        request["approval_status"] = "approved"
        request["status"] = "scheduled"
        request["approver_member_id"] = _required("approver_member_id", approver_member_id)
        request["scheduled_at"] = _timestamp(_coerce_datetime(scheduled_at or self._now()))
        request["updated_at"] = _timestamp(self._now())
        self._audit(
            action="data_deletion.approved",
            request=request,
            actor_member_id=request["approver_member_id"],
            decision="approved",
        )
        return deepcopy(request)

    def reject_request(
        self,
        request_id: str,
        *,
        approver_member_id: str,
        reason: str | None = None,
    ) -> dict[str, Any]:
        request = self._require(request_id)
        if request["approval_status"] != "pending":
            raise ValueError("invalid_approval_status")
        request["approval_status"] = "rejected"
        request["status"] = "rejected"
        request["approver_member_id"] = _required("approver_member_id", approver_member_id)
        request["rejection_reason"] = reason
        request["updated_at"] = _timestamp(self._now())
        self._audit(
            action="data_deletion.rejected",
            request=request,
            actor_member_id=request["approver_member_id"],
            decision="rejected",
        )
        return deepcopy(request)

    def due_requests(self, *, at: datetime | str | None = None) -> list[dict[str, Any]]:
        cutoff = _coerce_datetime(at or self._now())
        due = []
        for request in self.requests.values():
            if request["approval_status"] != "approved":
                continue
            if request["status"] != "scheduled":
                continue
            if request["scheduled_at"] is None:
                continue
            if _coerce_datetime(request["scheduled_at"]) <= cutoff:
                due.append(deepcopy(request))
        return sorted(due, key=lambda item: (item["scheduled_at"], item["id"]))

    def run_due_requests(self, *, at: datetime | str | None = None) -> list[dict[str, Any]]:
        ready = []
        for due in self.due_requests(at=at):
            request = self.requests[due["id"]]
            request["status"] = "ready_for_worker"
            request["execution_plan"] = _execution_plan(request)
            request["updated_at"] = _timestamp(self._now())
            self._audit(
                action="data_deletion.ready_for_worker",
                request=request,
                actor_member_id=request["approver_member_id"],
                decision="ready",
            )
            ready.append(deepcopy(request))
        return ready

    def mark_completed(
        self,
        request_id: str,
        *,
        completed_by_member_id: str,
    ) -> dict[str, Any]:
        request = self._require(request_id)
        if request["status"] != "ready_for_worker":
            raise ValueError("request_not_approved")
        request["status"] = "completed"
        request["completed_at"] = _timestamp(self._now())
        request["updated_at"] = request["completed_at"]
        self._audit(
            action="data_deletion.completed",
            request=request,
            actor_member_id=_required("completed_by_member_id", completed_by_member_id),
            decision="completed",
        )
        return deepcopy(request)

    def _require(self, request_id: str) -> dict[str, Any]:
        normalized = _required("deletion_request_id", request_id)
        request = self.requests.get(normalized)
        if request is None:
            raise KeyError(normalized)
        return request

    def _audit(
        self,
        *,
        action: str,
        request: dict[str, Any],
        actor_member_id: str | None,
        decision: str,
    ) -> None:
        if self.audit_log is None:
            return
        self.audit_log.record(
            org_id=request["org_id"],
            actor_member_id=actor_member_id,
            actor_type="member" if actor_member_id else "system",
            action=action,
            resource_type="data_deletion_request",
            resource_id=request["id"],
            decision=decision,
            metadata={
                "target_type": request["target_type"],
                "target_id": request["target_id"],
                "mode": request["mode"],
                "export_before_delete": request["export_before_delete"],
                "export_id": request["export_id"],
                "approval_status": request["approval_status"],
                "status": request["status"],
            },
        )


def _execution_plan(request: dict[str, Any]) -> list[str]:
    plan = ["disable_access"]
    if request["export_before_delete"]:
        plan.append("export_before_delete")
    plan.extend(
        [
            "delete_relationships",
            "soft_delete_rows",
            "delete_objects",
            "hard_delete_rows_after_retention",
            "write_final_audit",
        ]
    )
    if request["mode"] == "anonymize":
        return ["disable_access", "anonymize_rows", "write_final_audit"]
    if request["mode"] == "soft_delete":
        return ["disable_access", "soft_delete_rows", "write_final_audit"]
    return plan


def _validate_target_type(value: str) -> str:
    normalized = str(value or "").strip()
    if normalized not in VALID_TARGET_TYPES:
        raise ValueError("invalid_target_type")
    return normalized


def _validate_mode(value: str) -> str:
    normalized = str(value or "").strip()
    if normalized not in VALID_DELETION_MODES:
        raise ValueError("invalid_deletion_mode")
    return normalized


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
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _timestamp(value: datetime) -> str:
    return _coerce_datetime(value).isoformat().replace("+00:00", "Z")


def _random_request_id() -> str:
    return f"delete-request-{secrets.token_hex(16)}"
