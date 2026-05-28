"""Team-mode tool policy hook for enterprise authorization."""

from __future__ import annotations

import re
from typing import Any, Callable, Mapping


_READ_TOOLS = {
    "read_file",
    "search_files",
    "vision_analyze",
    "list_files",
}
_WRITE_TOOLS = {
    "write_file",
    "patch",
    "apply_patch",
    "skill_manage",
    "image_generate",
    "text_to_speech",
}
_NETWORK_TOOLS = {
    "web_search",
    "web_extract",
    "browser_navigate",
    "browser_click",
    "fetch",
}
_DESTRUCTIVE_TERMINAL_RE = re.compile(
    r"\b(rm\s+-rf|mkfs|dd\s+if=|chmod\s+-r|chown\s+-r|docker\s+system\s+prune|kubectl\s+delete)\b",
    re.IGNORECASE,
)


def build_default_approval_callback() -> Callable[..., None]:
    """Return a placeholder callback for future approval integration."""

    def _noop(*_args: Any, **_kwargs: Any) -> None:
        return None

    return _noop


class TeamToolPolicyHook:
    """Fail-closed pre-tool-call authorization hook for team mode."""

    def __init__(self, *, authz_client: Any, approval_callback: Callable[..., Any] | None = None) -> None:
        self.authz_client = authz_client
        self.approval_callback = approval_callback or build_default_approval_callback()

    def pre_tool_call(
        self,
        *,
        tool_name: str,
        args: Mapping[str, Any] | None = None,
        team_context: Mapping[str, Any] | None = None,
        user_id: str = "",
        **_kwargs: Any,
    ) -> dict[str, str] | None:
        org_id = str((team_context or {}).get("org_id") or "").strip()
        member_id = str((team_context or {}).get("member_id") or user_id or "").strip()
        if not org_id or not member_id:
            return self._block("team_actor_missing")
        if self.authz_client is None:
            return self._block("authorization_unavailable")

        payload = {
            "org_id": org_id,
            "resource_type": "organization",
            "resource_id": org_id,
            "permission": permission_for_tool(tool_name, args or {}),
            "subject_type": "member",
            "subject_id": member_id,
        }
        try:
            allowed = _authz_allowed(self.authz_client, payload)
        except Exception:
            return self._block("authorization_unavailable")
        if not allowed:
            return self._block("permission_denied")
        return None

    @staticmethod
    def _block(message: str) -> dict[str, str]:
        return {"action": "block", "message": message}


def permission_for_tool(tool_name: str, args: Mapping[str, Any]) -> str:
    """Map a Hermes tool call to the organization-level execution permission."""
    name = str(tool_name or "").strip().lower()
    if name in _READ_TOOLS:
        return "file_read_execute"
    if name in _WRITE_TOOLS:
        return "file_write_execute"
    if name in _NETWORK_TOOLS or name.startswith("web_") or name.startswith("browser_"):
        return "network_execute"
    if name in {"terminal", "shell", "exec_command"}:
        command = str(args.get("cmd") or args.get("command") or "").strip()
        if _DESTRUCTIVE_TERMINAL_RE.search(command):
            return "destructive_execute"
        return "terminal_execute"
    if name in {"secret", "credential", "delete", "destroy"}:
        return "destructive_execute"
    return "safe_execute"


def _authz_allowed(client: Any, payload: dict[str, str]) -> bool:
    for method_name in ("check_permission", "check", "CheckPermission"):
        method = getattr(client, method_name, None)
        if method is None:
            continue
        return _decision_allowed(method(payload))
    if callable(client):
        return _decision_allowed(client(payload))
    raise RuntimeError("authz_client_missing_check")


def _decision_allowed(decision: Any) -> bool:
    if isinstance(decision, bool):
        return decision
    if isinstance(decision, Mapping):
        return bool(decision.get("allowed") or decision.get("Allowed"))
    return bool(getattr(decision, "allowed", False) or getattr(decision, "Allowed", False))


__all__ = [
    "TeamToolPolicyHook",
    "build_default_approval_callback",
    "permission_for_tool",
]
