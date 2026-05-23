"""Team Web Chat run primitives."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from team_cloud.correlation import build_correlation_context


class ChatRunNotFound(KeyError):
    """Raised when a chat run id is unknown."""


class InMemoryChatRunService:
    """Small in-memory run store for local Web Chat wiring and tests."""

    def __init__(self, *, cloud_session_repository: Any | None = None) -> None:
        self._counter = 0
        self._runs: dict[str, dict[str, Any]] = {}
        self.cloud_session_repository = cloud_session_repository

    def create_run(
        self,
        *,
        org_id: str,
        team_id: str,
        project_id: str,
        member_id: str,
        message: str,
        cloud_session_id: str | None = None,
        request_id: str | None = None,
        trace_id: str | None = None,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        org_id = _required("org_id", org_id)
        team_id = _required("team_id", team_id)
        project_id = _required("project_id", project_id)
        member_id = _required("member_id", member_id)
        message = _required("message", message)

        self._counter += 1
        run_id = f"run-{self._counter}"
        created_at = _timestamp()
        correlation = build_correlation_context(
            request_id=request_id,
            run_id=run_id,
            trace_id=trace_id,
            correlation_id=correlation_id,
        )
        cloud_session_id = self._record_cloud_history(
            run_id=run_id,
            org_id=org_id,
            team_id=team_id,
            project_id=project_id,
            member_id=member_id,
            message=message,
            cloud_session_id=cloud_session_id,
        )
        events = [
            _event(
                run_id=run_id,
                sequence=1,
                event_type="chat.run.created",
                payload={
                    "org_id": org_id,
                    "team_id": team_id,
                    "project_id": project_id,
                    "member_id": member_id,
                    "status": "queued",
                    "cloud_session_id": cloud_session_id,
                },
                request_id=correlation["request_id"],
                trace_id=correlation["trace_id"],
                correlation_id=correlation["correlation_id"],
            ),
            _event(
                run_id=run_id,
                sequence=2,
                event_type="chat.message.accepted",
                payload={"message_preview": message[:200]},
                request_id=correlation["request_id"],
                trace_id=correlation["trace_id"],
                correlation_id=correlation["correlation_id"],
            ),
        ]
        run = {
            "id": run_id,
            "org_id": org_id,
            "team_id": team_id,
            "project_id": project_id,
            "member_id": member_id,
            "message": message,
            "cloud_session_id": cloud_session_id,
            "status": "queued",
            "created_at": created_at,
            "events": events,
            **correlation,
        }
        self._runs[run_id] = run
        return deepcopy(run)

    def list_events(self, run_id: str) -> list[dict[str, Any]]:
        run = self._runs.get(str(run_id or "").strip())
        if run is None:
            raise ChatRunNotFound(run_id)
        return deepcopy(run["events"])

    def append_event(
        self,
        *,
        run_id: str,
        event_type: str,
        payload: dict[str, Any],
        request_id: str | None = None,
        trace_id: str | None = None,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        run = self._runs.get(str(run_id or "").strip())
        if run is None:
            raise ChatRunNotFound(run_id)
        if not isinstance(payload, dict):
            raise ValueError("payload_must_be_object")
        event = _event(
            run_id=run["id"],
            sequence=len(run["events"]) + 1,
            event_type=_required("event_type", event_type),
            payload=payload,
            request_id=request_id or run.get("request_id"),
            trace_id=trace_id or run.get("trace_id"),
            correlation_id=correlation_id or run.get("correlation_id"),
        )
        run["events"].append(event)
        if isinstance(payload.get("status"), str) and payload["status"].strip():
            run["status"] = payload["status"].strip()
        return deepcopy(event)

    def _record_cloud_history(
        self,
        *,
        run_id: str,
        org_id: str,
        team_id: str,
        project_id: str,
        member_id: str,
        message: str,
        cloud_session_id: str | None,
    ) -> str | None:
        repository = self.cloud_session_repository
        if repository is None:
            return None
        if cloud_session_id:
            session_id = str(cloud_session_id).strip()
        else:
            session = repository.create_session(
                org_id=org_id,
                team_id=team_id,
                project_id=project_id,
                owner_member_id=member_id,
                title=message,
                source_platform="web",
            )
            session_id = session["id"]
        repository.append_message(
            session_id=session_id,
            org_id=org_id,
            role="user",
            content={"text": message},
            run_id=run_id,
        )
        return session_id


def _event(
    *,
    run_id: str,
    sequence: int,
    event_type: str,
    payload: dict[str, Any],
    request_id: str | None = None,
    audit_event_id: str | None = None,
    trace_id: str | None = None,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    correlation = build_correlation_context(
        request_id=request_id,
        run_id=run_id,
        audit_event_id=audit_event_id,
        trace_id=trace_id,
        correlation_id=correlation_id,
    )
    return {
        "id": f"{run_id}-event-{sequence}",
        "run_id": run_id,
        "sequence": sequence,
        "type": event_type,
        "payload": payload,
        "created_at": _timestamp(),
        **correlation,
    }


def _required(field_name: str, value: Any) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{field_name}_required")
    return normalized


def _timestamp() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
