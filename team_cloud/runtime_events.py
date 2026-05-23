"""Runtime event bridge for Team Cloud chat history."""

from __future__ import annotations

from typing import Any

from team_cloud.chat import ChatRunNotFound
from team_cloud.cloud_sessions import CloudSessionNotFound
from team_cloud.correlation import build_correlation_context


MESSAGE_EVENTS = {"message.completed", "assistant.message", "tool.message"}
TOOL_EVENTS = {"tool.completed", "tool.failed"}


class RuntimeEventBridge:
    def __init__(self, *, cloud_session_repository: Any, chat_run_service: Any) -> None:
        self.cloud_session_repository = cloud_session_repository
        self.chat_run_service = chat_run_service

    def ingest(self, payload: dict[str, Any]) -> dict[str, Any]:
        org_id = _required("org_id", payload.get("org_id"))
        run_id = _required("run_id", payload.get("run_id"))
        cloud_session_id = _required("cloud_session_id", payload.get("cloud_session_id"))
        event_type = _required("type", payload.get("type"))
        raw_event_payload = payload.get("payload") or {}
        if not isinstance(raw_event_payload, dict):
            raise ValueError("payload_must_be_object")
        event_payload = dict(raw_event_payload)
        correlation = build_correlation_context(
            request_id=payload.get("request_id") or event_payload.get("request_id"),
            run_id=run_id,
            trace_id=payload.get("trace_id") or event_payload.get("trace_id"),
            correlation_id=payload.get("correlation_id")
            or event_payload.get("correlation_id"),
        )
        event_payload.setdefault("request_id", correlation["request_id"])
        event_payload.setdefault("trace_id", correlation["trace_id"])
        event_payload.setdefault("correlation_id", correlation["correlation_id"])

        session = self.cloud_session_repository.get_session(cloud_session_id)
        if session["org_id"] != org_id:
            raise ValueError("org_id_mismatch")

        message = None
        tool_call = None
        if event_type in MESSAGE_EVENTS:
            message = self._record_message(
                org_id=org_id,
                run_id=run_id,
                cloud_session_id=cloud_session_id,
                event_payload=event_payload,
            )
        elif event_type in TOOL_EVENTS:
            tool_call = self._record_tool_call(
                org_id=org_id,
                run_id=run_id,
                cloud_session_id=cloud_session_id,
                event_payload=event_payload,
            )

        event = self.chat_run_service.append_event(
            run_id=run_id,
            event_type=event_type,
            payload=event_payload,
            request_id=correlation["request_id"],
            trace_id=correlation["trace_id"],
            correlation_id=correlation["correlation_id"],
        )
        return {
            "accepted": True,
            "event": event,
            "message": message,
            "tool_call": tool_call,
        }

    def _record_message(
        self,
        *,
        org_id: str,
        run_id: str,
        cloud_session_id: str,
        event_payload: dict[str, Any],
    ) -> dict[str, Any]:
        role = str(event_payload.get("role") or "assistant").strip()
        content = event_payload.get("content")
        if content is None:
            content = event_payload.get("text", "")
        if isinstance(content, dict):
            message_content = content
        else:
            message_content = {"text": str(content or "")}
        return self.cloud_session_repository.append_message(
            session_id=cloud_session_id,
            org_id=org_id,
            role=role,
            content=message_content,
            run_id=run_id,
        )

    def _record_tool_call(
        self,
        *,
        org_id: str,
        run_id: str,
        cloud_session_id: str,
        event_payload: dict[str, Any],
    ) -> dict[str, Any]:
        return self.cloud_session_repository.append_tool_call(
            session_id=cloud_session_id,
            org_id=org_id,
            actor_member_id=event_payload.get("actor_member_id"),
            tool_name=event_payload["tool_name"],
            risk_level=event_payload.get("risk_level", "safe"),
            decision=event_payload.get("decision", "allowed"),
            input_redacted=event_payload.get("input_redacted", {}),
            output_redacted=event_payload.get("output_redacted"),
            error=event_payload.get("error"),
            run_id=run_id,
        )


def _required(field_name: str, value: Any) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{field_name}_required")
    return normalized


__all__ = [
    "ChatRunNotFound",
    "CloudSessionNotFound",
    "RuntimeEventBridge",
]
