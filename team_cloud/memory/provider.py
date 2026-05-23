"""Team Cloud memory provider core adapter.

This module intentionally does not register an in-tree plugins/memory provider.
It is the reusable provider core that a standalone Team Cloud memory plugin can
import without violating the repository policy that closes new bundled memory
providers.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Protocol
from urllib import request

from agent.memory_provider import MemoryProvider


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
    personal_memory_enabled: bool = True

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

    def initialize(self, session_id: str, **kwargs) -> None:
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
                "Search personal and team memory.",
                {"query": "string", "limit": "integer"},
                required=("query",),
            ),
            _tool_schema(
                "team_memory_remember",
                "Remember a personal memory.",
                {
                    "content": "string",
                    "memory_type": "string",
                    "sensitivity": "string",
                },
                required=("content",),
            ),
            _tool_schema(
                "team_memory_propose",
                "Propose a team shared memory.",
                {
                    "content": "string",
                    "memory_type": "string",
                    "sensitivity": "string",
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
                "Archive a memory.",
                {"memory_id": "string"},
                required=("memory_id",),
            ),
            _tool_schema(
                "team_memory_backup_now",
                "Run a personal memory backup.",
                {},
            ),
        ]

    def handle_tool_call(self, tool_name: str, args: dict[str, Any], **kwargs) -> str:
        if not self.is_available():
            return _json_result(success=False, error="inactive")
        context = self._context()
        try:
            if tool_name == "team_memory_search":
                return self._tool_search(args, context)
            if tool_name == "team_memory_remember":
                return self._tool_remember(args, context)
            if tool_name == "team_memory_propose":
                return self._tool_propose(args, context)
            if tool_name == "team_memory_promote":
                return self._tool_promote(args, context)
            if tool_name == "team_memory_forget":
                return self._tool_forget(args, context)
            if tool_name == "team_memory_backup_now":
                return self._tool_backup_now(args, context)
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
            },
            headers=self._headers(),
        )
        return _json_result(success=True, data=response)

    def _tool_remember(self, args: dict[str, Any], context: TeamContext) -> str:
        action = "memory.personal.write"
        if not self._allowed(action=action, args=args, context=context):
            return _json_result(success=False, error="permission_denied")
        response = self.http_client.post_json(
            "/v1/memory",
            json={
                "org_id": context.org_id,
                "scope": "personal",
                "subject_member_id": context.member_id,
                "content": args["content"],
                "memory_type": args.get("memory_type", "fact"),
                "sensitivity": args.get("sensitivity", "normal"),
            },
            headers=self._headers(),
        )
        return _json_result(success=True, data=response)

    def _tool_propose(self, args: dict[str, Any], context: TeamContext) -> str:
        action = "memory.team.propose"
        if not self._allowed(action=action, args=args, context=context):
            return _json_result(success=False, error="permission_denied")
        response = self.http_client.post_json(
            "/v1/memory",
            json={
                "org_id": context.org_id,
                "scope": "team_shared",
                "team_id": context.team_id,
                "project_id": context.project_id,
                "content": args["content"],
                "memory_type": args.get("memory_type", "fact"),
                "sensitivity": args.get("sensitivity", "normal"),
            },
            headers=self._headers(),
        )
        return _json_result(success=True, data=response)

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
        action = "memory.personal.write"
        if not self._allowed(action=action, args=args, context=context):
            return _json_result(success=False, error="permission_denied")
        response = self.http_client.post_json(
            f"/v1/memory/{args['memory_id']}/archive",
            json={"actor_member_id": context.member_id},
            headers=self._headers(),
        )
        return _json_result(success=True, data=response)

    def _tool_backup_now(self, args: dict[str, Any], context: TeamContext) -> str:
        action = "backup.create"
        if not self._allowed(action=action, args=args, context=context):
            return _json_result(success=False, error="permission_denied")
        response = self.http_client.post_json(
            "/v1/backups/personal/run",
            json={
                "org_id": context.org_id,
                "member_id": context.member_id,
            },
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
    properties: dict[str, str],
    *,
    required: tuple[str, ...] = (),
) -> dict[str, Any]:
    return {
        "name": name,
        "description": description,
        "parameters": {
            "type": "object",
            "properties": {
                key: {"type": value}
                for key, value in properties.items()
            },
            "required": list(required),
        },
    }


def _json_result(
    *,
    success: bool,
    data: dict[str, Any] | None = None,
    error: str | None = None,
) -> str:
    payload: dict[str, Any] = {"success": success}
    if data is not None:
        payload["data"] = data
    if error is not None:
        payload["error"] = error
    return json.dumps(payload, sort_keys=True)


def json_module_dumps(value: dict[str, Any]) -> str:
    return json.dumps(value, separators=(",", ":"))


def json_module_loads(value: str) -> dict[str, Any]:
    if not value:
        return {}
    loaded = json.loads(value)
    if not isinstance(loaded, dict):
        raise ValueError("Team Cloud response must be a JSON object")
    return loaded
