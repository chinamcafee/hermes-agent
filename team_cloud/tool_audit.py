"""Tool audit sink for Team Cloud policy decisions."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import re
from typing import Any, Protocol


_SECRET_KEY_RE = re.compile(
    r"(api[_-]?key|token|password|passwd|secret|credential|private[_-]?key)",
    re.IGNORECASE,
)


class ToolAuditSink(Protocol):
    def record_tool_policy_event(
        self,
        *,
        metadata: Mapping[str, Any],
        decision: str,
        input_redacted: Mapping[str, Any],
        error: str | None = None,
    ) -> dict[str, Any]: ...


class TeamToolAuditSink:
    """Write tool policy outcomes to cloud tool history and audit log."""

    def __init__(self, *, cloud_session_repository: Any = None, audit_log: Any = None):
        self.cloud_session_repository = cloud_session_repository
        self.audit_log = audit_log

    def record_tool_policy_event(
        self,
        *,
        metadata: Mapping[str, Any],
        decision: str,
        input_redacted: Mapping[str, Any],
        error: str | None = None,
    ) -> dict[str, Any]:
        normalized_decision = cloud_tool_decision(decision)
        tool_call = None
        audit_event = None
        if self.cloud_session_repository is not None:
            tool_call = self._append_tool_call(
                metadata=metadata,
                decision=normalized_decision,
                input_redacted=input_redacted,
                error=error,
            )
        if self.audit_log is not None:
            audit_event = self._record_audit_event(
                metadata=metadata,
                decision=normalized_decision,
                input_redacted=input_redacted,
                error=error,
            )
        return {"tool_call": tool_call, "audit_event": audit_event}

    def _append_tool_call(
        self,
        *,
        metadata: Mapping[str, Any],
        decision: str,
        input_redacted: Mapping[str, Any],
        error: str | None,
    ) -> dict[str, Any] | None:
        session_id = _first(metadata, "cloud_session_id", "session_id")
        org_id = _first(metadata, "org_id")
        if not session_id or not org_id:
            return None
        return self.cloud_session_repository.append_tool_call(
            session_id=session_id,
            org_id=org_id,
            actor_member_id=_first(metadata, "actor_member_id", "member_id"),
            tool_name=_first(metadata, "tool_name") or "unknown",
            risk_level=cloud_tool_risk_level(
                _first(metadata, "risk_level"),
                _first(metadata, "permission"),
            ),
            decision=decision,
            input_redacted=dict(input_redacted),
            error=error,
            run_id=_first(metadata, "run_id", "task_id"),
        )

    def _record_audit_event(
        self,
        *,
        metadata: Mapping[str, Any],
        decision: str,
        input_redacted: Mapping[str, Any],
        error: str | None,
    ) -> dict[str, Any]:
        action = f"tool.call.{decision}"
        audit_metadata = {
            "tool_name": _first(metadata, "tool_name") or "unknown",
            "risk_level": _first(metadata, "risk_level"),
            "cloud_risk_level": cloud_tool_risk_level(
                _first(metadata, "risk_level"),
                _first(metadata, "permission"),
            ),
            "permission": _first(metadata, "permission"),
            "reason": _first(metadata, "reason"),
            "approval_choice": _first(metadata, "approval_choice"),
            "session_id": _first(metadata, "session_id"),
            "cloud_session_id": _first(metadata, "cloud_session_id"),
            "run_id": _first(metadata, "run_id", "task_id"),
            "input_redacted": deepcopy(dict(input_redacted)),
        }
        if error:
            audit_metadata["error"] = error
        return self.audit_log.record(
            action=action,
            org_id=_first(metadata, "org_id") or None,
            actor_member_id=_first(metadata, "actor_member_id", "member_id") or None,
            actor_type=_first(metadata, "actor_type") or "user",
            resource_type="tool",
            resource_id=_first(metadata, "tool_name") or "unknown",
            decision=decision,
            request_id=_first(metadata, "request_id") or None,
            metadata=audit_metadata,
        )


def cloud_tool_decision(decision: str) -> str:
    normalized = str(decision or "").strip().lower()
    if normalized in {"allowed", "denied", "approval_required", "approved", "rejected", "error"}:
        return normalized
    return "error"


def cloud_tool_risk_level(risk_level: str, permission: str = "") -> str:
    risk = str(risk_level or "").strip().lower()
    resolved_permission = str(permission or "").strip().lower()
    if risk == "file":
        if resolved_permission == "file_read_execute":
            return "file_read"
        return "file_write"
    if risk == "secret":
        return "destructive"
    if risk in {"safe", "network", "file_read", "file_write", "terminal", "destructive"}:
        return risk
    return "safe"


def redact_tool_args(value: Any) -> Any:
    if isinstance(value, Mapping):
        redacted: dict[str, Any] = {}
        for key, nested in value.items():
            if _SECRET_KEY_RE.search(str(key)):
                redacted[str(key)] = "[REDACTED]"
            else:
                redacted[str(key)] = redact_tool_args(nested)
        return redacted
    if isinstance(value, list):
        return [redact_tool_args(item) for item in value]
    if isinstance(value, tuple):
        return [redact_tool_args(item) for item in value]
    return deepcopy(value)


def _first(metadata: Mapping[str, Any], *keys: str) -> str:
    for key in keys:
        value = metadata.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""
