"""Import local Hermes SessionDB history into Team Cloud sessions."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
import json
import sqlite3
from typing import Any


_CONTENT_JSON_PREFIX = "\x00json:"
_VALID_CLOUD_ROLES = {"system", "user", "assistant", "tool"}


def import_sessiondb(
    db_path: str | Path,
    cloud_session_repository: Any,
    *,
    org_id: str,
    team_id: str,
    project_id: str,
    identity_map: Mapping[str, str],
    default_member_id: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Import mapped SessionDB sessions into a cloud session repository."""
    db_path = Path(db_path)
    if not db_path.exists():
        raise FileNotFoundError(db_path)

    normalized_identity_map = {
        str(key).strip(): str(value).strip()
        for key, value in dict(identity_map).items()
        if str(key).strip() and str(value).strip()
    }
    default_member_id = str(default_member_id or "").strip() or None

    imported_sessions: list[dict[str, Any]] = []
    unmapped_sessions: list[dict[str, Any]] = []
    imported_message_count = 0

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        for session in _read_sessions(conn):
            member_id = _resolve_member_id(
                session["user_id"],
                identity_map=normalized_identity_map,
                default_member_id=default_member_id,
            )
            if member_id is None:
                unmapped_sessions.append(
                    {
                        "local_session_id": session["id"],
                        "source": session["source"],
                        "user_id": session["user_id"],
                        "reason": "identity_not_mapped",
                    }
                )
                continue

            messages = _read_messages(conn, session["id"])
            cloud_session_id = None
            if not dry_run:
                cloud_session = cloud_session_repository.create_session(
                    org_id=org_id,
                    team_id=team_id,
                    project_id=project_id,
                    owner_member_id=member_id,
                    title=session["title"] or f"Imported {session['id']}",
                    source_platform=f"sessiondb:{session['source'] or 'unknown'}",
                )
                cloud_session_id = cloud_session["id"]
                for message in messages:
                    cloud_session_repository.append_message(
                        session_id=cloud_session_id,
                        org_id=org_id,
                        role=_cloud_role(message["role"]),
                        content=_cloud_message_content(message),
                        token_count=message["token_count"],
                    )

            imported_message_count += len(messages)
            imported_sessions.append(
                {
                    "local_session_id": session["id"],
                    "cloud_session_id": cloud_session_id,
                    "member_id": member_id,
                    "source": session["source"],
                    "message_count": len(messages),
                }
            )

    return {
        "schema_version": 1,
        "source": "sessiondb",
        "dry_run": dry_run,
        "imported_session_count": len(imported_sessions),
        "imported_message_count": imported_message_count,
        "unmapped_session_count": len(unmapped_sessions),
        "imported_sessions": imported_sessions,
        "unmapped_sessions": unmapped_sessions,
    }


def _read_sessions(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return list(
        conn.execute(
            """
            SELECT id, source, user_id, title, started_at
            FROM sessions
            ORDER BY started_at ASC, id ASC
            """
        )
    )


def _read_messages(conn: sqlite3.Connection, session_id: str) -> list[sqlite3.Row]:
    return list(
        conn.execute(
            """
            SELECT id, role, content, tool_call_id, tool_calls, tool_name, token_count
            FROM messages
            WHERE session_id = ?
            ORDER BY id ASC
            """,
            (session_id,),
        )
    )


def _resolve_member_id(
    user_id: str | None,
    *,
    identity_map: Mapping[str, str],
    default_member_id: str | None,
) -> str | None:
    normalized_user_id = str(user_id or "").strip()
    if normalized_user_id and normalized_user_id in identity_map:
        return identity_map[normalized_user_id]
    return default_member_id


def _cloud_role(role: str | None) -> str:
    normalized = str(role or "").strip()
    if normalized in _VALID_CLOUD_ROLES:
        return normalized
    return "assistant"


def _cloud_message_content(message: sqlite3.Row) -> dict[str, Any]:
    content = _decode_content(message["content"])
    if isinstance(content, str) or content is None:
        payload: dict[str, Any] = {"text": content or ""}
    else:
        payload = {"content": content}

    payload["local_message_id"] = message["id"]
    if message["tool_call_id"]:
        payload["tool_call_id"] = message["tool_call_id"]
    if message["tool_name"]:
        payload["tool_name"] = message["tool_name"]
    tool_calls = _decode_json_field(message["tool_calls"])
    if tool_calls is not None:
        payload["tool_calls"] = tool_calls
    return payload


def _decode_content(content: Any) -> Any:
    if isinstance(content, str) and content.startswith(_CONTENT_JSON_PREFIX):
        try:
            return json.loads(content[len(_CONTENT_JSON_PREFIX) :])
        except json.JSONDecodeError:
            return content
    return content


def _decode_json_field(value: Any) -> Any:
    if value in (None, ""):
        return None
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return value
