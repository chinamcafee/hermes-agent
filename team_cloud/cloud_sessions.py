"""Cloud session history primitives for Team Cloud."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any


class CloudSessionNotFound(KeyError):
    """Raised when a cloud session id is unknown."""


class InMemoryCloudSessionRepository:
    """In-memory cloud session/message/tool-call store for local runtime wiring."""

    VALID_ROLES = {"system", "user", "assistant", "tool"}
    VALID_RISK_LEVELS = {
        "safe",
        "network",
        "file_read",
        "file_write",
        "terminal",
        "destructive",
    }
    VALID_DECISIONS = {
        "allowed",
        "denied",
        "approval_required",
        "approved",
        "rejected",
        "error",
    }

    def __init__(self) -> None:
        self._session_counter = 0
        self._message_counter = 0
        self._tool_call_counter = 0
        self._sessions: dict[str, dict[str, Any]] = {}

    def create_session(
        self,
        *,
        org_id: str,
        team_id: str,
        project_id: str,
        owner_member_id: str,
        title: str = "",
        source_platform: str = "web",
    ) -> dict[str, Any]:
        org_id = _required("org_id", org_id)
        team_id = _required("team_id", team_id)
        project_id = _required("project_id", project_id)
        owner_member_id = _required("owner_member_id", owner_member_id)
        self._session_counter += 1
        session_id = f"cloud-session-{self._session_counter}"
        now = _timestamp()
        session = {
            "id": session_id,
            "org_id": org_id,
            "team_id": team_id,
            "project_id": project_id,
            "owner_member_id": owner_member_id,
            "title": str(title or "").strip()[:120],
            "source_platform": str(source_platform or "web").strip() or "web",
            "status": "active",
            "created_at": now,
            "updated_at": now,
            "messages": [],
            "tool_calls": [],
        }
        self._sessions[session_id] = session
        return deepcopy(session)

    def append_message(
        self,
        *,
        session_id: str,
        org_id: str,
        role: str,
        content: dict[str, Any],
        run_id: str | None = None,
        token_count: int | None = None,
    ) -> dict[str, Any]:
        session = self._get_mutable(session_id)
        if _required("org_id", org_id) != session["org_id"]:
            raise ValueError("org_id_mismatch")
        role = _required("role", role)
        if role not in self.VALID_ROLES:
            raise ValueError("invalid_message_role")
        if not isinstance(content, dict):
            raise ValueError("content_must_be_object")

        self._message_counter += 1
        message = {
            "id": f"cloud-message-{self._message_counter}",
            "org_id": session["org_id"],
            "session_id": session["id"],
            "run_id": str(run_id or "").strip() or None,
            "role": role,
            "content": deepcopy(content),
            "token_count": token_count,
            "created_at": _timestamp(),
        }
        session["messages"].append(message)
        session["updated_at"] = message["created_at"]
        return deepcopy(message)

    def append_tool_call(
        self,
        *,
        session_id: str,
        org_id: str,
        actor_member_id: str | None,
        tool_name: str,
        risk_level: str,
        decision: str,
        input_redacted: dict[str, Any],
        output_redacted: dict[str, Any] | None = None,
        error: str | None = None,
        run_id: str | None = None,
    ) -> dict[str, Any]:
        session = self._get_mutable(session_id)
        if _required("org_id", org_id) != session["org_id"]:
            raise ValueError("org_id_mismatch")
        risk_level = _required("risk_level", risk_level)
        decision = _required("decision", decision)
        if risk_level not in self.VALID_RISK_LEVELS:
            raise ValueError("invalid_risk_level")
        if decision not in self.VALID_DECISIONS:
            raise ValueError("invalid_decision")
        if not isinstance(input_redacted, dict):
            raise ValueError("input_redacted_must_be_object")
        if output_redacted is not None and not isinstance(output_redacted, dict):
            raise ValueError("output_redacted_must_be_object")

        self._tool_call_counter += 1
        now = _timestamp()
        tool_call = {
            "id": f"cloud-tool-call-{self._tool_call_counter}",
            "org_id": session["org_id"],
            "session_id": session["id"],
            "run_id": str(run_id or "").strip() or None,
            "actor_member_id": str(actor_member_id or "").strip() or None,
            "tool_name": _required("tool_name", tool_name),
            "risk_level": risk_level,
            "decision": decision,
            "input_redacted": deepcopy(input_redacted),
            "output_redacted": deepcopy(output_redacted),
            "error": str(error or "").strip() or None,
            "created_at": now,
        }
        session["tool_calls"].append(tool_call)
        session["updated_at"] = now
        return deepcopy(tool_call)

    def get_session(self, session_id: str) -> dict[str, Any]:
        return deepcopy(self._get_mutable(session_id))

    def list_sessions(
        self,
        *,
        org_id: str | None = None,
        project_id: str | None = None,
        member_id: str | None = None,
        q: str | None = None,
    ) -> list[dict[str, Any]]:
        query = str(q or "").strip().lower()
        items = []
        for session in self._sessions.values():
            if org_id and session["org_id"] != org_id:
                continue
            if project_id and session["project_id"] != project_id:
                continue
            if member_id and session["owner_member_id"] != member_id:
                continue
            if query and query not in _search_text(session):
                continue
            items.append(_summary(session))
        return sorted(items, key=lambda item: item["updated_at"], reverse=True)

    def _get_mutable(self, session_id: str) -> dict[str, Any]:
        normalized = str(session_id or "").strip()
        session = self._sessions.get(normalized)
        if session is None:
            raise CloudSessionNotFound(normalized)
        return session


def _summary(session: dict[str, Any]) -> dict[str, Any]:
    return {
        key: deepcopy(session[key])
        for key in (
            "id",
            "org_id",
            "team_id",
            "project_id",
            "owner_member_id",
            "title",
            "source_platform",
            "status",
            "created_at",
            "updated_at",
        )
    } | {
        "message_count": len(session["messages"]),
        "tool_call_count": len(session["tool_calls"]),
    }


def _search_text(session: dict[str, Any]) -> str:
    parts = [session.get("title", "")]
    for message in session.get("messages", []):
        content = message.get("content", {})
        if isinstance(content, dict):
            parts.extend(str(value) for value in content.values())
    return " ".join(parts).lower()


def _required(field_name: str, value: Any) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{field_name}_required")
    return normalized


def _timestamp() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
