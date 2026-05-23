"""Team Cloud tool execution policy hook."""

from __future__ import annotations

from collections.abc import Mapping
import json
from typing import Any, Callable, Protocol

from team_cloud.authz.spicedb import PermissionDecision, ResourceRef, SubjectRef
from team_cloud.tool_audit import ToolAuditSink, redact_tool_args
from team_cloud.tool_risk import RiskCategory, classify_tool_call, risk_requires_approval


TEAM_TOOL_POLICY_CONSISTENCY = "fully_consistent_for_sensitive"
APPROVAL_ALLOW_CHOICES = frozenset(
    {"once", "session", "always", "approve", "approved", "allow", "allowed", "yes", "y"}
)
APPROVAL_TIMEOUT_CHOICES = frozenset({"timeout", "timed_out", "expired"})
BLOCK_DECISION_BY_REASON = {
    "team_actor_missing": "denied",
    "permission_denied": "denied",
    "approval_denied": "rejected",
    "approval_timeout": "error",
    "authorization_unavailable": "error",
    "approval_unavailable": "error",
    "audit_unavailable": "error",
}

FILE_READ_TOOLS = frozenset({"read_file", "search_files", "vision_analyze"})
FILE_WRITE_TOOLS = frozenset(
    {"write_file", "patch", "skill_manage", "image_generate", "text_to_speech"}
)

RISK_PERMISSION_MAP: dict[RiskCategory, str] = {
    "safe": "safe_execute",
    "network": "network_execute",
    "file": "file_write_execute",
    "terminal": "terminal_execute",
    "destructive": "destructive_execute",
    "secret": "destructive_execute",
}


class ToolPolicyAuthzClient(Protocol):
    def check(
        self,
        *,
        subject: SubjectRef,
        resource: ResourceRef,
        permission: str,
        consistency: str,
    ) -> PermissionDecision: ...


ToolApprovalCallback = Callable[..., str | dict[str, Any] | None]


class TeamToolPolicyHook:
    """Fail-closed pre-tool-call policy hook for Team Cloud sessions."""

    def __init__(
        self,
        *,
        authz_client: ToolPolicyAuthzClient | None,
        approval_callback: ToolApprovalCallback | None = None,
        audit_sink: ToolAuditSink | None = None,
        consistency: str = TEAM_TOOL_POLICY_CONSISTENCY,
    ) -> None:
        self.authz_client = authz_client
        self.approval_callback = approval_callback
        self.audit_sink = audit_sink
        self.consistency = consistency

    def pre_tool_call(
        self,
        *,
        tool_name: str = "",
        args: Mapping[str, Any] | None = None,
        task_id: str = "",
        session_id: str = "",
        tool_call_id: str = "",
        team_context: Any = None,
        platform: str = "",
        user_id: str = "",
        **_: Any,
    ) -> dict[str, Any] | None:
        normalized_tool = str(tool_name or "").strip() or "unknown"
        normalized_args = dict(args or {})
        input_redacted = redact_tool_args(normalized_args)
        risk_level = classify_tool_call(normalized_tool, normalized_args)
        permission = tool_permission_for_call(normalized_tool, risk_level)
        subject = subject_for_team_context(team_context)
        resource = ResourceRef("tool", normalized_tool)
        metadata = self._metadata(
            tool_name=normalized_tool,
            risk_level=risk_level,
            permission=permission,
            subject=subject,
            resource=resource,
            task_id=task_id,
            session_id=session_id,
            tool_call_id=tool_call_id,
            team_context=team_context,
            platform=platform,
            user_id=user_id,
        )
        metadata["input_redacted"] = input_redacted

        if subject is None:
            return self._block(
                "team_actor_missing",
                f"[team_tool_policy:team_actor_missing] Tool {normalized_tool} blocked because no Team Cloud actor context was provided.",
                metadata,
            )
        if self.authz_client is None:
            return self._block(
                "authorization_unavailable",
                f"[team_tool_policy:authorization_unavailable] Tool {normalized_tool} blocked because Team Cloud authorization is unavailable.",
                metadata,
            )

        try:
            decision = self.authz_client.check(
                subject=subject,
                resource=resource,
                permission=permission,
                consistency=self.consistency,
            )
        except Exception as exc:
            metadata["error"] = type(exc).__name__
            return self._block(
                "authorization_unavailable",
                f"[team_tool_policy:authorization_unavailable] Tool {normalized_tool} blocked because Team Cloud authorization failed.",
                metadata,
            )

        metadata["authz_reason"] = decision.reason
        if decision.reason == "spicedb_error":
            return self._block(
                "authorization_unavailable",
                f"[team_tool_policy:authorization_unavailable] Tool {normalized_tool} blocked because SpiceDB returned an unavailable decision.",
                metadata,
            )
        if not decision.allowed:
            return self._block(
                "permission_denied",
                f"[team_tool_policy:permission_denied] Tool {normalized_tool} blocked by Team Cloud policy.",
                metadata,
            )
        approval_block = self._approval_block_if_needed(
            tool_name=normalized_tool,
            args=normalized_args,
            risk_level=risk_level,
            permission=permission,
            metadata=metadata,
        )
        if approval_block is not None:
            return approval_block
        audit_error = self._record_tool_audit(
            metadata,
            decision="approved" if metadata.get("approval_choice") else "allowed",
        )
        if audit_error:
            metadata["error"] = audit_error
            return self._block(
                "audit_unavailable",
                f"[team_tool_policy:audit_unavailable] Tool {normalized_tool} blocked because Team Cloud tool audit failed.",
                metadata,
                record_audit=False,
            )
        return None

    def _approval_block_if_needed(
        self,
        *,
        tool_name: str,
        args: dict[str, Any],
        risk_level: RiskCategory,
        permission: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any] | None:
        if not risk_requires_approval(risk_level):
            return None
        if self.approval_callback is None:
            return self._block(
                "approval_unavailable",
                f"[team_tool_policy:approval_unavailable] Tool {tool_name} blocked because no Team Cloud approval gate is available.",
                metadata,
            )
        try:
            raw_choice = self.approval_callback(
                tool_name=tool_name,
                args=args,
                risk_level=risk_level,
                permission=permission,
                metadata=dict(metadata),
            )
        except Exception as exc:
            metadata["error"] = type(exc).__name__
            return self._block(
                "approval_unavailable",
                f"[team_tool_policy:approval_unavailable] Tool {tool_name} blocked because Team Cloud approval failed.",
                metadata,
            )

        choice = _normalize_approval_choice(raw_choice)
        metadata["approval_choice"] = choice
        if choice in APPROVAL_ALLOW_CHOICES:
            return None
        if choice in APPROVAL_TIMEOUT_CHOICES:
            return self._block(
                "approval_timeout",
                f"[team_tool_policy:approval_timeout] Tool {tool_name} blocked because Team Cloud approval timed out.",
                metadata,
            )
        return self._block(
            "approval_denied",
            f"[team_tool_policy:approval_denied] Tool {tool_name} blocked by Team Cloud approval.",
            metadata,
        )

    def _metadata(
        self,
        *,
        tool_name: str,
        risk_level: RiskCategory,
        permission: str,
        subject: SubjectRef | None,
        resource: ResourceRef,
        task_id: str,
        session_id: str,
        tool_call_id: str,
        team_context: Any,
        platform: str,
        user_id: str,
    ) -> dict[str, Any]:
        return {
            "tool_name": tool_name,
            "risk_level": risk_level,
            "permission": permission,
            "subject": subject.as_spicedb() if subject is not None else "",
            "resource": resource.as_spicedb(),
            "consistency": self.consistency,
            "task_id": task_id,
            "session_id": session_id,
            "tool_call_id": tool_call_id,
            "platform": platform,
            "user_id": user_id,
            "org_id": _context_value(team_context, "org_id"),
            "team_id": _context_value(team_context, "team_id"),
            "project_id": _context_value(team_context, "project_id"),
            "actor_member_id": _context_value(team_context, "member_id"),
            "member_id": _context_value(team_context, "member_id"),
            "actor_type": _context_value(team_context, "actor_type") or "user",
            "cloud_session_id": _context_value(team_context, "cloud_session_id"),
            "run_id": _context_value(team_context, "run_id") or task_id,
        }

    def _block(
        self,
        reason: str,
        message: str,
        metadata: dict[str, Any],
        *,
        record_audit: bool = True,
    ) -> dict[str, Any]:
        if record_audit:
            self._record_tool_audit(
                {**metadata, "reason": reason},
                decision=BLOCK_DECISION_BY_REASON.get(reason, "error"),
                error=reason,
            )
        return {
            "action": "block",
            "message": message,
            "metadata": {**metadata, "reason": reason},
        }

    def _record_tool_audit(
        self,
        metadata: dict[str, Any],
        *,
        decision: str,
        error: str | None = None,
    ) -> str | None:
        if self.audit_sink is None:
            return None
        try:
            input_redacted = metadata.get("input_redacted")
            if not isinstance(input_redacted, Mapping):
                input_redacted = {}
            self.audit_sink.record_tool_policy_event(
                metadata=metadata,
                decision=decision,
                input_redacted=input_redacted,
                error=error,
            )
            return None
        except Exception as exc:
            return type(exc).__name__


def tool_permission_for_call(
    tool_name: str,
    risk_level: RiskCategory | None = None,
) -> str:
    """Return the SpiceDB tool permission for a classified tool call."""
    normalized_tool = str(tool_name or "").strip()
    if normalized_tool in FILE_READ_TOOLS:
        return "file_read_execute"
    if normalized_tool in FILE_WRITE_TOOLS:
        return "file_write_execute"
    risk = risk_level or classify_tool_call(normalized_tool, {})
    return RISK_PERMISSION_MAP[risk]


def subject_for_team_context(team_context: Any) -> SubjectRef | None:
    """Extract a SpiceDB subject from a dict-like Team Cloud context."""
    actor_type = str(
        _context_value(team_context, "actor_type")
        or _context_value(team_context, "subject_type")
        or "user"
    ).strip().lower()
    service_account_id = _context_value(team_context, "service_account_id")
    member_id = (
        _context_value(team_context, "member_id")
        or _context_value(team_context, "actor_id")
        or _context_value(team_context, "user_id")
    )
    if actor_type in {"service_account", "service-account", "service"}:
        subject_id = service_account_id or member_id
        return SubjectRef("service_account", subject_id) if subject_id else None
    subject_id = member_id or service_account_id
    return SubjectRef("user", subject_id) if subject_id else None


def build_default_approval_callback() -> ToolApprovalCallback:
    """Build a Hermes approval callback for high-risk Team Cloud tool calls."""

    def _approve(**kwargs: Any) -> str:
        from tools.approval import prompt_dangerous_approval
        from tools.terminal_tool import _get_approval_callback

        tool_name = str(kwargs.get("tool_name") or "unknown")
        args = kwargs.get("args") if isinstance(kwargs.get("args"), dict) else {}
        risk_level = str(kwargs.get("risk_level") or "unknown")
        command = _approval_subject(tool_name, args)
        description = f"Team Cloud {risk_level} tool approval required for {tool_name}"
        return prompt_dangerous_approval(
            command,
            description,
            allow_permanent=False,
            approval_callback=_get_approval_callback(),
        )

    return _approve


def _normalize_approval_choice(choice: str | dict[str, Any] | None) -> str:
    if isinstance(choice, Mapping):
        if choice.get("approved") is True:
            return str(choice.get("choice") or "once").strip().lower()
        if choice.get("status") == "timeout":
            return "timeout"
        return str(choice.get("choice") or "deny").strip().lower()
    return str(choice or "deny").strip().lower()


def _approval_subject(tool_name: str, args: Mapping[str, Any]) -> str:
    if tool_name == "terminal":
        command = args.get("command") or args.get("cmd")
        if command:
            return str(command)
    try:
        rendered_args = json.dumps(args, ensure_ascii=False, sort_keys=True)
    except TypeError:
        rendered_args = str(dict(args))
    if len(rendered_args) > 1200:
        rendered_args = rendered_args[:1200] + "...[truncated]"
    return f"{tool_name} {rendered_args}"


def _context_value(team_context: Any, key: str) -> str:
    if isinstance(team_context, Mapping):
        value = team_context.get(key)
    else:
        value = getattr(team_context, key, None)
    return str(value).strip() if value is not None else ""
