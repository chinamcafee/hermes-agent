"""Team Cloud memory provider used by Hermes runtime team mode.

The cloud service itself is implemented by the Go ``team_cloud`` service. This
Python module is only the local runtime adapter that calls that service from the
Hermes Agent memory-manager surface.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Protocol
from urllib import request

from agent.memory_provider import MemoryProvider


ALLOWED_MEMORY_TYPES = ("fact", "preference", "procedure", "policy", "constraint", "summary")
ALLOWED_SENSITIVITIES = ("normal", "pii", "secret", "restricted")

MEMORY_TYPE_ALIASES = {
    "company": "fact",
    "company_fact": "fact",
    "company_info": "fact",
    "general": "fact",
    "info": "fact",
    "information": "fact",
    "how_to": "procedure",
    "process": "procedure",
    "rule": "policy",
}


class TeamCloudHttpClient(Protocol):
    def post_json(
        self,
        path: str,
        *,
        json: dict[str, Any],
        headers: dict[str, str],
    ) -> dict[str, Any]: ...


class TeamMemoryPermissionChecker(Protocol):
    def check(
        self,
        *,
        action: str,
        args: dict[str, Any],
        context: "TeamContext",
    ) -> bool: ...


@dataclass(frozen=True)
class TeamContext:
    org_id: str
    team_id: str
    member_id: str
    project_id: str | None = None
    personal_memory_enabled: bool = False

    def is_complete(self) -> bool:
        return bool(self.org_id and self.team_id and self.member_id)


@dataclass(frozen=True)
class TeamMemoryProviderConfig:
    team_cloud_url: str
    service_token: str
    team_context: TeamContext | None
    prefetch_limit: int = 8


class UrllibTeamCloudHttpClient:
    def __init__(self, *, base_url: str, timeout_seconds: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def post_json(
        self,
        path: str,
        *,
        json: dict[str, Any],
        headers: dict[str, str],
    ) -> dict[str, Any]:
        body = json_module_dumps(json).encode("utf-8")
        req = request.Request(
            f"{self.base_url}{path}",
            data=body,
            headers={
                **headers,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        with request.urlopen(req, timeout=self.timeout_seconds) as response:  # noqa: S310
            payload = response.read().decode("utf-8")
        return json_module_loads(payload)


class TeamMemoryProvider(MemoryProvider):
    def __init__(
        self,
        *,
        config: TeamMemoryProviderConfig,
        http_client: TeamCloudHttpClient | None = None,
        permission_checker: TeamMemoryPermissionChecker | None = None,
    ) -> None:
        self.config = config
        self.http_client = http_client or UrllibTeamCloudHttpClient(
            base_url=config.team_cloud_url,
        )
        self.permission_checker = permission_checker
        self._session_id = ""
        self.last_error: str | None = None

    @property
    def name(self) -> str:
        return "team_cloud"

    def is_available(self) -> bool:
        context = self.config.team_context
        return bool(
            self.config.team_cloud_url
            and self.config.service_token
            and context is not None
            and context.is_complete()
        )

    def initialize(self, session_id: str, **kwargs: Any) -> None:
        self._session_id = session_id
        self.last_error = None

    def prefetch(self, query: str, *, session_id: str = "") -> str:
        if not self.is_available():
            return ""
        context = self._context()
        try:
            response = self.http_client.post_json(
                "/v1/memory/prefetch",
                json={
                    "query": query,
                    "org_id": context.org_id,
                    "member_id": context.member_id,
                    "team_id": context.team_id,
                    "project_id": context.project_id,
                    "limit": self.config.prefetch_limit,
                    "include_personal": context.personal_memory_enabled,
                },
                headers=self._headers(),
            )
        except Exception as exc:
            self.last_error = str(exc)
            return ""
        return _format_prefetch_context(response)

    def sync_turn(
        self,
        user_content: str,
        assistant_content: str,
        *,
        session_id: str = "",
        turn_metadata: dict[str, Any] | None = None,
        tool_summaries: list[dict[str, Any]] | None = None,
    ) -> None:
        if not self.is_available():
            return
        context = self._context()
        observation: dict[str, Any] = {
            "source": "hermes_turn",
            "messages": [
                {"role": "user", "content": user_content},
                {"role": "assistant", "content": assistant_content},
            ],
        }
        if turn_metadata is not None:
            observation["turn_metadata"] = dict(turn_metadata)
        if tool_summaries is not None:
            observation["tool_summaries"] = list(tool_summaries)
        try:
            self.http_client.post_json(
                "/v1/memory/observations",
                json={
                    "org_id": context.org_id,
                    "session_id": session_id or self._session_id,
                    "member_id": context.member_id,
                    "team_id": context.team_id,
                    "project_id": context.project_id,
                    "observation": observation,
                },
                headers=self._headers(),
            )
        except Exception as exc:
            self.last_error = str(exc)

    def get_tool_schemas(self) -> list[dict[str, Any]]:
        return [
            _tool_schema(
                "team_memory_search",
                "Search team memory.",
                {"query": "string", "limit": "integer"},
                required=("query",),
            ),
            _tool_schema(
                "team_memory_add",
                "Create an active team shared memory when the user explicitly asks to add team memory.",
                {
                    "content": "string",
                    "memory_type": {"type": "string", "enum": list(ALLOWED_MEMORY_TYPES)},
                    "sensitivity": {"type": "string", "enum": list(ALLOWED_SENSITIVITIES)},
                },
                required=("content",),
            ),
            _tool_schema(
                "team_memory_propose",
                "Propose an automatically extracted team shared memory; do not use for explicit user add requests.",
                {
                    "content": "string",
                    "memory_type": {"type": "string", "enum": list(ALLOWED_MEMORY_TYPES)},
                    "sensitivity": {"type": "string", "enum": list(ALLOWED_SENSITIVITIES)},
                },
                required=("content",),
            ),
            _tool_schema(
                "team_memory_promote",
                "Promote personal memory to team review.",
                {"memory_id": "string"},
                required=("memory_id",),
            ),
            _tool_schema(
                "team_memory_forget",
                "Archive a team memory.",
                {"memory_id": "string"},
                required=("memory_id",),
            ),
        ]

    def system_prompt_block(self) -> str:
        return (
            "Team Cloud memory tools are available.\n"
            "- Use team_memory_add only when the user explicitly asks to create, add, or save a team memory.\n"
            "- For explicit team-memory requests, never use team_memory_propose and never fall back to personal memory.\n"
            "- Use team_memory_propose only after automatic team-memory extraction and tell the user the memory id.\n"
            "- Do not call the local memory tool for explicit team-memory requests.\n"
            "- Do not store local personal memory in Team Cloud; local personal memory remains local.\n"
        )

    def handle_tool_call(self, tool_name: str, args: dict[str, Any], **kwargs: Any) -> str:
        if not self.is_available():
            return _json_result(success=False, error="inactive")
        context = self._context()
        try:
            if tool_name == "team_memory_search":
                return self._tool_search(args, context)
            if tool_name == "team_memory_add":
                return self._tool_add(args, context)
            if tool_name == "team_memory_propose":
                return self._tool_propose(args, context)
            if tool_name == "team_memory_promote":
                return self._tool_promote(args, context)
            if tool_name == "team_memory_forget":
                return self._tool_forget(args, context)
        except Exception as exc:
            self.last_error = str(exc)
            return _json_result(success=False, error=str(exc))
        return _json_result(success=False, error="unknown_tool")

    def _context(self) -> TeamContext:
        context = self.config.team_context
        if context is None:
            raise RuntimeError("team context is not configured")
        return context

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.config.service_token}"}

    def _tool_search(self, args: dict[str, Any], context: TeamContext) -> str:
        response = self.http_client.post_json(
            "/v1/memory/prefetch",
            json={
                "query": args["query"],
                "org_id": context.org_id,
                "member_id": context.member_id,
                "team_id": context.team_id,
                "project_id": context.project_id,
                "limit": int(args.get("limit", self.config.prefetch_limit)),
                "include_personal": context.personal_memory_enabled,
            },
            headers=self._headers(),
        )
        return _json_result(success=True, data=response)

    def _tool_add(self, args: dict[str, Any], context: TeamContext) -> str:
        action = "memory.team.write"
        normalized_args = _normalize_memory_write_args(args)
        if not self._allowed(action=action, args=normalized_args, context=context):
            return _json_result(success=False, error="permission_denied")
        response = self.http_client.post_json(
            "/v1/memory",
            json={
                "org_id": context.org_id,
                "scope": "team_shared",
                "team_id": context.team_id,
                "project_id": context.project_id,
                "created_by_member_id": context.member_id,
                "status": "active",
                "source_type": "admin_created",
                "content": normalized_args["content"],
                "memory_type": normalized_args["memory_type"],
                "sensitivity": normalized_args["sensitivity"],
            },
            headers=self._headers(),
        )
        memory_id = str(response.get("id") or "")
        content = str(response.get("content") or normalized_args["content"])
        notice = f"团队记忆已创建：{memory_id} - {content}" if memory_id else f"团队记忆已创建：{content}"
        return _json_result(success=True, data=response, notice=notice)

    def _tool_propose(self, args: dict[str, Any], context: TeamContext) -> str:
        action = "memory.team.propose"
        normalized_args = _normalize_memory_write_args(args)
        if not self._allowed(action=action, args=normalized_args, context=context):
            return _json_result(success=False, error="permission_denied")
        response = self.http_client.post_json(
            "/v1/memory",
            json={
                "org_id": context.org_id,
                "scope": "team_shared",
                "team_id": context.team_id,
                "project_id": context.project_id,
                "created_by_member_id": context.member_id,
                "status": "active",
                "source_type": "auto_extracted",
                "content": normalized_args["content"],
                "memory_type": normalized_args["memory_type"],
                "sensitivity": normalized_args["sensitivity"],
            },
            headers=self._headers(),
        )
        memory_id = str(response.get("id") or "")
        content = str(response.get("content") or normalized_args["content"])
        notice = f"团队记忆已抽取：{memory_id} - {content}" if memory_id else f"团队记忆已抽取：{content}"
        return _json_result(success=True, data=response, notice=notice)

    def _tool_promote(self, args: dict[str, Any], context: TeamContext) -> str:
        action = "memory.team.propose"
        if not self._allowed(action=action, args=args, context=context):
            return _json_result(success=False, error="permission_denied")
        response = self.http_client.post_json(
            f"/v1/memory/{args['memory_id']}/promote",
            json={
                "org_id": context.org_id,
                "team_id": context.team_id,
                "project_id": context.project_id,
                "actor_member_id": context.member_id,
            },
            headers=self._headers(),
        )
        return _json_result(success=True, data=response)

    def _tool_forget(self, args: dict[str, Any], context: TeamContext) -> str:
        action = "memory.team.write"
        if not self._allowed(action=action, args=args, context=context):
            return _json_result(success=False, error="permission_denied")
        response = self.http_client.post_json(
            f"/v1/memory/{args['memory_id']}/archive",
            json={"actor_member_id": context.member_id},
            headers=self._headers(),
        )
        return _json_result(success=True, data=response)

    def _allowed(
        self,
        *,
        action: str,
        args: dict[str, Any],
        context: TeamContext,
    ) -> bool:
        if self.permission_checker is None:
            return True
        return bool(
            self.permission_checker.check(
                action=action,
                args=args,
                context=context,
            )
        )


def team_context_from_mapping(value: dict[str, Any] | None) -> TeamContext | None:
    if not isinstance(value, dict):
        return None
    context = TeamContext(
        org_id=str(value.get("org_id") or "").strip(),
        team_id=str(value.get("team_id") or "").strip(),
        member_id=str(value.get("member_id") or "").strip(),
        project_id=str(value.get("project_id") or "").strip() or None,
        personal_memory_enabled=bool(value.get("personal_memory_enabled", False)),
    )
    return context if context.is_complete() else None


def _format_prefetch_context(response: dict[str, Any]) -> str:
    lines = []
    for partition in response.get("partitions", []):
        scope = partition.get("scope", "unknown")
        for item in partition.get("items", []):
            memory_id = item.get("id", "unknown")
            memory_type = item.get("memory_type", "memory")
            sensitivity = item.get("sensitivity", "normal")
            content = item.get("content", "")
            if content:
                lines.append(
                    f"- [{scope}:{memory_id} {memory_type}/{sensitivity}] {content}"
                )
    if not lines:
        return ""
    return "Team Cloud memory:\n" + "\n".join(lines)


def _tool_schema(
    name: str,
    description: str,
    properties: dict[str, Any],
    *,
    required: tuple[str, ...] = (),
) -> dict[str, Any]:
    return {
        "name": name,
        "description": description,
        "parameters": {
            "type": "object",
            "properties": {
                key: value if isinstance(value, dict) else {"type": value}
                for key, value in properties.items()
            },
            "required": list(required),
        },
    }


def _normalize_memory_write_args(args: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(args)
    normalized["content"] = str(args.get("content") or "")
    normalized["memory_type"] = _normalize_memory_type(args.get("memory_type"))
    normalized["sensitivity"] = _normalize_sensitivity(args.get("sensitivity"))
    return normalized


def _normalize_memory_type(value: Any) -> str:
    normalized = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    normalized = MEMORY_TYPE_ALIASES.get(normalized, normalized)
    if normalized in ALLOWED_MEMORY_TYPES:
        return normalized
    return "fact"


def _normalize_sensitivity(value: Any) -> str:
    normalized = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if normalized in ALLOWED_SENSITIVITIES:
        return normalized
    return "normal"


def _json_result(
    *,
    success: bool,
    data: dict[str, Any] | None = None,
    error: str | None = None,
    notice: str | None = None,
) -> str:
    payload: dict[str, Any] = {"success": success}
    if data is not None:
        payload["data"] = data
    if error is not None:
        payload["error"] = error
    if notice is not None:
        payload["notice"] = notice
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def json_module_dumps(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def json_module_loads(value: str) -> dict[str, Any]:
    if not value:
        return {}
    loaded = json.loads(value)
    if not isinstance(loaded, dict):
        raise ValueError("Team Cloud response must be a JSON object")
    return loaded


__all__ = [
    "TeamCloudHttpClient",
    "TeamContext",
    "TeamMemoryPermissionChecker",
    "TeamMemoryProvider",
    "TeamMemoryProviderConfig",
    "UrllibTeamCloudHttpClient",
    "team_context_from_mapping",
]
