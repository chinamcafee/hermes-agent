"""Retention policy planning and in-memory enforcement."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Callable


VALID_RESOURCE_TYPES = {"session", "tool_call", "memory", "audit_event"}
VALID_ACTIONS = {"archive", "soft_delete", "hard_delete"}


class RetentionPolicyService:
    """Stores retention policies and applies them to Team Cloud repositories."""

    def __init__(
        self,
        *,
        audit_log: Any | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.audit_log = audit_log
        self._now = now or (lambda: datetime.now(UTC))
        self.policies: dict[tuple[str, str], dict[str, Any]] = {}

    def upsert_policy(
        self,
        *,
        org_id: str,
        resource_type: str,
        retain_for_days: int,
        action: str,
    ) -> dict[str, Any]:
        org_id = _required("org_id", org_id)
        resource_type = _validate_resource_type(resource_type)
        action = _validate_action(action)
        retain_for_days = _validate_days(retain_for_days)
        policy = {
            "org_id": org_id,
            "resource_type": resource_type,
            "retain_for_days": retain_for_days,
            "action": action,
            "updated_at": _timestamp(self._now()),
        }
        self.policies[(org_id, resource_type)] = policy
        return dict(policy)

    def plan_retention(
        self,
        *,
        org_id: str,
        cloud_session_repository: Any | None = None,
        memory_service: Any | None = None,
        audit_log: Any | None = None,
        at: datetime | None = None,
    ) -> dict[str, list[dict[str, Any]]]:
        org_id = _required("org_id", org_id)
        cutoff_base = at or self._now()
        actions: list[dict[str, Any]] = []
        skipped: list[dict[str, Any]] = []
        self._plan_sessions(
            org_id=org_id,
            cutoff_base=cutoff_base,
            cloud_session_repository=cloud_session_repository,
            actions=actions,
            skipped=skipped,
        )
        self._plan_tool_calls(
            org_id=org_id,
            cutoff_base=cutoff_base,
            cloud_session_repository=cloud_session_repository,
            actions=actions,
            skipped=skipped,
        )
        self._plan_memory(
            org_id=org_id,
            cutoff_base=cutoff_base,
            memory_service=memory_service,
            actions=actions,
            skipped=skipped,
        )
        self._plan_audit(
            org_id=org_id,
            cutoff_base=cutoff_base,
            audit_log=audit_log,
            actions=actions,
            skipped=skipped,
        )
        actions.sort(key=lambda item: (item["resource_type"], item["resource_id"]))
        skipped.sort(key=lambda item: (item["resource_type"], item["resource_id"]))
        return {"actions": actions, "skipped": skipped}

    def apply_retention(
        self,
        actions: list[dict[str, Any]],
        *,
        cloud_session_repository: Any | None = None,
        memory_service: Any | None = None,
        audit_log: Any | None = None,
    ) -> dict[str, int]:
        summary = {"applied": 0, "failed": 0}
        for action_item in actions:
            try:
                self._apply_action(
                    action_item,
                    cloud_session_repository=cloud_session_repository,
                    memory_service=memory_service,
                    audit_log=audit_log,
                )
            except Exception:
                summary["failed"] += 1
                continue
            summary["applied"] += 1
            self._audit_applied(action_item)
        return summary

    def _plan_sessions(
        self,
        *,
        org_id: str,
        cutoff_base: datetime,
        cloud_session_repository: Any | None,
        actions: list[dict[str, Any]],
        skipped: list[dict[str, Any]],
    ) -> None:
        policy = self.policies.get((org_id, "session"))
        sessions = getattr(cloud_session_repository, "_sessions", None)
        if policy is None or not isinstance(sessions, dict):
            return
        for session in sessions.values():
            if session.get("org_id") != org_id:
                continue
            self._append_plan_item(
                policy=policy,
                record=session,
                timestamp=session.get("updated_at") or session.get("created_at"),
                cutoff_base=cutoff_base,
                actions=actions,
                skipped=skipped,
            )

    def _plan_tool_calls(
        self,
        *,
        org_id: str,
        cutoff_base: datetime,
        cloud_session_repository: Any | None,
        actions: list[dict[str, Any]],
        skipped: list[dict[str, Any]],
    ) -> None:
        policy = self.policies.get((org_id, "tool_call"))
        sessions = getattr(cloud_session_repository, "_sessions", None)
        if policy is None or not isinstance(sessions, dict):
            return
        for session in sessions.values():
            if session.get("org_id") != org_id:
                continue
            for tool_call in session.get("tool_calls", []):
                record = {**tool_call, "session_id": session["id"]}
                self._append_plan_item(
                    policy=policy,
                    record=record,
                    timestamp=tool_call.get("created_at"),
                    cutoff_base=cutoff_base,
                    actions=actions,
                    skipped=skipped,
                )

    def _plan_memory(
        self,
        *,
        org_id: str,
        cutoff_base: datetime,
        memory_service: Any | None,
        actions: list[dict[str, Any]],
        skipped: list[dict[str, Any]],
    ) -> None:
        policy = self.policies.get((org_id, "memory"))
        items = getattr(memory_service, "items", None)
        if policy is None or not isinstance(items, dict):
            return
        for memory in items.values():
            if memory.get("org_id") != org_id:
                continue
            self._append_plan_item(
                policy=policy,
                record=memory,
                timestamp=memory.get("updated_at") or memory.get("created_at"),
                cutoff_base=cutoff_base,
                actions=actions,
                skipped=skipped,
            )

    def _plan_audit(
        self,
        *,
        org_id: str,
        cutoff_base: datetime,
        audit_log: Any | None,
        actions: list[dict[str, Any]],
        skipped: list[dict[str, Any]],
    ) -> None:
        policy = self.policies.get((org_id, "audit_event"))
        events = getattr(audit_log, "events", None)
        if policy is None or not isinstance(events, list):
            return
        for event in events:
            if event.get("org_id") != org_id:
                continue
            self._append_plan_item(
                policy=policy,
                record=event,
                timestamp=event.get("created_at"),
                cutoff_base=cutoff_base,
                actions=actions,
                skipped=skipped,
            )

    def _append_plan_item(
        self,
        *,
        policy: dict[str, Any],
        record: dict[str, Any],
        timestamp: Any,
        cutoff_base: datetime,
        actions: list[dict[str, Any]],
        skipped: list[dict[str, Any]],
    ) -> None:
        if not _is_expired(timestamp, cutoff_base, policy["retain_for_days"]):
            return
        item = {
            "org_id": policy["org_id"],
            "resource_type": policy["resource_type"],
            "resource_id": record["id"],
            "action": policy["action"],
            "retain_for_days": policy["retain_for_days"],
            "due_at": _timestamp(_coerce_datetime(timestamp) + timedelta(days=policy["retain_for_days"])),
        }
        if _has_legal_hold(record):
            skipped.append({**item, "reason": "legal_hold"})
            return
        actions.append(item)

    def _apply_action(
        self,
        action_item: dict[str, Any],
        *,
        cloud_session_repository: Any | None,
        memory_service: Any | None,
        audit_log: Any | None,
    ) -> None:
        resource_type = action_item["resource_type"]
        if resource_type == "session":
            _apply_session_action(action_item, cloud_session_repository, self._now())
            return
        if resource_type == "tool_call":
            _apply_tool_call_action(action_item, cloud_session_repository)
            return
        if resource_type == "memory":
            _apply_memory_action(action_item, memory_service)
            return
        if resource_type == "audit_event":
            _apply_audit_action(action_item, audit_log)
            return
        raise ValueError("invalid_retention_resource_type")

    def _audit_applied(self, action_item: dict[str, Any]) -> None:
        if self.audit_log is None:
            return
        self.audit_log.record(
            org_id=action_item["org_id"],
            actor_type="system",
            action="data_retention.applied",
            resource_type=action_item["resource_type"],
            resource_id=action_item["resource_id"],
            decision=action_item["action"],
            metadata={
                "retain_for_days": action_item["retain_for_days"],
                "due_at": action_item["due_at"],
            },
        )


def _apply_session_action(
    action_item: dict[str, Any],
    cloud_session_repository: Any | None,
    now: datetime,
) -> None:
    sessions = getattr(cloud_session_repository, "_sessions", None)
    if not isinstance(sessions, dict):
        return
    session_id = action_item["resource_id"]
    if action_item["action"] == "hard_delete":
        sessions.pop(session_id, None)
        return
    session = sessions.get(session_id)
    if session is not None:
        session["status"] = "archived" if action_item["action"] == "archive" else "deleted"
        session["updated_at"] = _timestamp(now)


def _apply_tool_call_action(
    action_item: dict[str, Any],
    cloud_session_repository: Any | None,
) -> None:
    sessions = getattr(cloud_session_repository, "_sessions", None)
    if not isinstance(sessions, dict):
        return
    tool_call_id = action_item["resource_id"]
    for session in sessions.values():
        session["tool_calls"] = [
            tool_call
            for tool_call in session.get("tool_calls", [])
            if tool_call.get("id") != tool_call_id
        ]


def _apply_memory_action(action_item: dict[str, Any], memory_service: Any | None) -> None:
    if memory_service is None:
        return
    memory_id = action_item["resource_id"]
    if action_item["action"] == "archive":
        memory_service.archive_memory(memory_id, actor_member_id="retention-worker")
        return
    if action_item["action"] == "soft_delete":
        memory_service.delete_memory(memory_id, actor_member_id="retention-worker")
        return
    items = getattr(memory_service, "items", {})
    items.pop(memory_id, None)
    events = getattr(memory_service, "events", None)
    if isinstance(events, list):
        events[:] = [event for event in events if event.get("memory_id") != memory_id]


def _apply_audit_action(action_item: dict[str, Any], audit_log: Any | None) -> None:
    events = getattr(audit_log, "events", None)
    if not isinstance(events, list):
        return
    event_id = action_item["resource_id"]
    events[:] = [event for event in events if event.get("id") != event_id]


def _is_expired(timestamp: Any, now: datetime, retain_for_days: int) -> bool:
    return _coerce_datetime(timestamp) + timedelta(days=retain_for_days) <= _coerce_datetime(now)


def _has_legal_hold(record: dict[str, Any]) -> bool:
    metadata = record.get("metadata")
    return bool(record.get("legal_hold")) or (
        isinstance(metadata, dict) and bool(metadata.get("legal_hold"))
    )


def _validate_resource_type(value: str) -> str:
    normalized = str(value or "").strip()
    if normalized not in VALID_RESOURCE_TYPES:
        raise ValueError("invalid_retention_resource_type")
    return normalized


def _validate_action(value: str) -> str:
    normalized = str(value or "").strip()
    if normalized not in VALID_ACTIONS:
        raise ValueError("invalid_retention_action")
    return normalized


def _validate_days(value: int) -> int:
    try:
        normalized = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid_retention_days") from exc
    if normalized <= 0:
        raise ValueError("invalid_retention_days")
    return normalized


def _required(field_name: str, value: Any) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{field_name}_required")
    return normalized


def _coerce_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _timestamp(value: datetime) -> str:
    return _coerce_datetime(value).isoformat().replace("+00:00", "Z")
