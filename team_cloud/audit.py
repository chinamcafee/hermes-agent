"""Audit event primitives for Team Cloud."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from copy import deepcopy
import json
import re
from typing import Any
from uuid import uuid4

from team_cloud.correlation import attach_correlation_fields


_SECRET_KEY_RE = re.compile(
    r"(api[_-]?key|token|password|passwd|secret|credential|private[_-]?key)",
    re.IGNORECASE,
)

_SENSITIVE_RESOURCE_TYPES = {
    "backup",
    "document",
    "memory",
    "personal_backup",
    "personal_memory",
}
_SENSITIVE_SCOPES = {"personal", "private", "break_glass"}
_SENSITIVE_LEVELS = {"restricted", "confidential", "secret", "high"}
_HIGH_RISK_TOOL_LEVELS = {"file_write", "terminal", "destructive"}


@dataclass
class InMemoryAuditLog:
    events: list[dict[str, Any]] = field(default_factory=list)

    def record(
        self,
        *,
        action: str,
        resource_type: str,
        org_id: str | None = None,
        actor_member_id: str | None = None,
        actor_type: str = "system",
        resource_id: str | None = None,
        decision: str = "recorded",
        request_id: str | None = None,
        run_id: str | None = None,
        trace_id: str | None = None,
        correlation_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        event_id = f"audit_{uuid4().hex}"
        event = attach_correlation_fields(
            {
                "id": event_id,
                "org_id": org_id,
                "actor_member_id": actor_member_id,
                "actor_type": actor_type,
                "action": action,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "decision": decision,
                "metadata": metadata or {},
                "created_at": datetime.now(UTC).isoformat(),
            },
            request_id=request_id,
            run_id=run_id,
            audit_event_id=event_id,
            trace_id=trace_id,
            correlation_id=correlation_id,
        )
        self.events.append(event)
        return event

    def query(
        self,
        *,
        org_id: str | None = None,
        action: str | None = None,
        actor_member_id: str | None = None,
        actor_type: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        decision: str | None = None,
        request_id: str | None = None,
        run_id: str | None = None,
        trace_id: str | None = None,
        correlation_id: str | None = None,
        created_after: str | None = None,
        created_before: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        results = self.events
        if org_id is not None:
            results = [event for event in results if event["org_id"] == org_id]
        if action is not None:
            results = [event for event in results if event["action"] == action]
        if actor_member_id is not None:
            results = [
                event
                for event in results
                if event["actor_member_id"] == actor_member_id
            ]
        if actor_type is not None:
            results = [event for event in results if event["actor_type"] == actor_type]
        if resource_type is not None:
            results = [event for event in results if event["resource_type"] == resource_type]
        if resource_id is not None:
            results = [event for event in results if event["resource_id"] == resource_id]
        if decision is not None:
            results = [event for event in results if event["decision"] == decision]
        if request_id is not None:
            results = [event for event in results if event["request_id"] == request_id]
        if run_id is not None:
            results = [event for event in results if event["run_id"] == run_id]
        if trace_id is not None:
            results = [event for event in results if event["trace_id"] == trace_id]
        if correlation_id is not None:
            results = [
                event for event in results if event["correlation_id"] == correlation_id
            ]
        after = _parse_timestamp(created_after)
        before = _parse_timestamp(created_before)
        if after is not None:
            results = [
                event
                for event in results
                if (_parse_timestamp(event.get("created_at")) or datetime.min.replace(tzinfo=UTC))
                >= after
            ]
        if before is not None:
            results = [
                event
                for event in results
                if (_parse_timestamp(event.get("created_at")) or datetime.max.replace(tzinfo=UTC))
                <= before
            ]
        return results[:limit]

    def sensitive_reads(
        self,
        *,
        org_id: str | None = None,
        actor_member_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        return [
            event
            for event in self.query(
                org_id=org_id,
                actor_member_id=actor_member_id,
                limit=len(self.events),
            )
            if _is_sensitive_read(event)
        ][:limit]

    def high_risk_tools(
        self,
        *,
        org_id: str | None = None,
        actor_member_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        return [
            event
            for event in self.query(
                org_id=org_id,
                actor_member_id=actor_member_id,
                limit=len(self.events),
            )
            if _is_high_risk_tool(event)
        ][:limit]

    def export_jsonl(self, **filters: Any) -> str:
        events = [_redact_event(event) for event in self.query(**filters)]
        if not events:
            return ""
        return "\n".join(
            json.dumps(event, ensure_ascii=False, sort_keys=True)
            for event in events
        ) + "\n"


def _parse_timestamp(value: Any) -> datetime | None:
    if value is None:
        return None
    normalized = str(value).strip()
    if not normalized:
        return None
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _is_sensitive_read(event: dict[str, Any]) -> bool:
    action = str(event.get("action") or "").lower()
    resource_type = str(event.get("resource_type") or "").lower()
    metadata = event.get("metadata") or {}
    if not isinstance(metadata, dict):
        metadata = {}
    scope = str(metadata.get("scope") or "").lower()
    sensitivity = str(metadata.get("sensitivity") or "").lower()
    return (
        action.endswith(".read")
        and (
            resource_type in _SENSITIVE_RESOURCE_TYPES
            or scope in _SENSITIVE_SCOPES
            or sensitivity in _SENSITIVE_LEVELS
        )
    ) or action in {"break_glass.accessed", "backup.read", "memory.read"}


def _is_high_risk_tool(event: dict[str, Any]) -> bool:
    if not str(event.get("action") or "").startswith("tool.call."):
        return False
    metadata = event.get("metadata") or {}
    if not isinstance(metadata, dict):
        metadata = {}
    cloud_risk = str(metadata.get("cloud_risk_level") or "").lower()
    risk = str(metadata.get("risk_level") or "").lower()
    return cloud_risk in _HIGH_RISK_TOOL_LEVELS or risk in _HIGH_RISK_TOOL_LEVELS


def _redact_event(event: dict[str, Any]) -> dict[str, Any]:
    return deepcopy(_redact_value(event))


def _redact_value(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, nested in value.items():
            if _SECRET_KEY_RE.search(str(key)):
                redacted[str(key)] = "[REDACTED]"
            else:
                redacted[str(key)] = _redact_value(nested)
        return redacted
    if isinstance(value, list):
        return [_redact_value(item) for item in value]
    if isinstance(value, tuple):
        return [_redact_value(item) for item in value]
    return value
