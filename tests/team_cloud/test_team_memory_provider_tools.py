from __future__ import annotations

import json


class FakeTeamCloudHttpClient:
    def __init__(self):
        self.calls = []
        self.responses = {}

    def post_json(self, path: str, *, json, headers):
        self.calls.append({"path": path, "json": json, "headers": headers})
        return self.responses.get(path, {"ok": True})


class FixedPermissionChecker:
    def __init__(self, allowed: bool):
        self.allowed = allowed
        self.calls = []

    def check(self, *, action, args, context):
        self.calls.append({"action": action, "args": args, "context": context})
        return self.allowed


def _provider(*, http_client=None, permission_checker=None):
    from team_cloud.memory.provider import (
        TeamContext,
        TeamMemoryProvider,
        TeamMemoryProviderConfig,
    )

    return TeamMemoryProvider(
        config=TeamMemoryProviderConfig(
            team_cloud_url="https://team-cloud.example",
            service_token="token-1",
            team_context=TeamContext(
                org_id="org-1",
                team_id="team-1",
                project_id="project-1",
                member_id="alice",
            ),
        ),
        http_client=http_client or FakeTeamCloudHttpClient(),
        permission_checker=permission_checker,
    )


def test_team_memory_provider_exposes_expected_tool_schemas():
    provider = _provider()

    schemas = provider.get_tool_schemas()

    assert [schema["name"] for schema in schemas] == [
        "team_memory_search",
        "team_memory_remember",
        "team_memory_propose",
        "team_memory_promote",
        "team_memory_forget",
        "team_memory_backup_now",
    ]
    assert all(schema["parameters"]["type"] == "object" for schema in schemas)


def test_team_memory_search_tool_returns_json_string_from_prefetch():
    http_client = FakeTeamCloudHttpClient()
    http_client.responses["/v1/memory/prefetch"] = {"memory_ids": ["mem-1"]}
    provider = _provider(http_client=http_client)

    result = json.loads(
        provider.handle_tool_call(
            "team_memory_search",
            {"query": "release", "limit": 3},
        )
    )

    assert result == {"success": True, "data": {"memory_ids": ["mem-1"]}}
    assert http_client.calls[0]["path"] == "/v1/memory/prefetch"
    assert http_client.calls[0]["json"]["limit"] == 3


def test_team_memory_remember_tool_checks_permission_and_creates_personal_memory():
    http_client = FakeTeamCloudHttpClient()
    checker = FixedPermissionChecker(True)
    provider = _provider(http_client=http_client, permission_checker=checker)

    result = json.loads(
        provider.handle_tool_call(
            "team_memory_remember",
            {"content": "Alice prefers deterministic tests.", "memory_type": "preference"},
        )
    )

    assert result["success"] is True
    assert checker.calls[0]["action"] == "memory.personal.write"
    assert http_client.calls[0] == {
        "path": "/v1/memory",
        "json": {
            "org_id": "org-1",
            "scope": "personal",
            "subject_member_id": "alice",
            "content": "Alice prefers deterministic tests.",
            "memory_type": "preference",
            "sensitivity": "normal",
        },
        "headers": {"Authorization": "Bearer token-1"},
    }


def test_team_memory_write_tool_denies_without_calling_team_cloud():
    http_client = FakeTeamCloudHttpClient()
    checker = FixedPermissionChecker(False)
    provider = _provider(http_client=http_client, permission_checker=checker)

    result = json.loads(
        provider.handle_tool_call(
            "team_memory_propose",
            {"content": "Team deploys on Fridays."},
        )
    )

    assert result == {"success": False, "error": "permission_denied"}
    assert checker.calls[0]["action"] == "memory.team.propose"
    assert http_client.calls == []
