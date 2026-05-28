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
    from agent.team_memory_provider import (
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
        "team_memory_add",
        "team_memory_propose",
        "team_memory_promote",
        "team_memory_forget",
    ]
    assert all(schema["parameters"]["type"] == "object" for schema in schemas)


def test_team_memory_provider_system_prompt_routes_explicit_team_memory_adds():
    provider = _provider()

    prompt = provider.system_prompt_block()

    assert "team_memory_add" in prompt
    assert "explicitly asks" in prompt
    assert "never use team_memory_propose" in prompt
    assert "Do not call the local memory tool" in prompt
    assert "local personal memory" in prompt


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


def test_team_memory_provider_does_not_manage_personal_memory_tools():
    http_client = FakeTeamCloudHttpClient()
    provider = _provider(http_client=http_client)

    result = json.loads(
        provider.handle_tool_call(
            "team_memory_remember",
            {"content": "Alice prefers deterministic tests.", "memory_type": "preference"},
        )
    )

    assert result == {"success": False, "error": "unknown_tool"}
    assert http_client.calls == []


def test_team_memory_add_tool_creates_active_team_memory_via_team_cloud():
    http_client = FakeTeamCloudHttpClient()
    http_client.responses["/v1/memory"] = {"id": "mem-team-1", "content": "任何时候都应该表明，我们是闻川网络科技公司。"}
    checker = FixedPermissionChecker(True)
    provider = _provider(http_client=http_client, permission_checker=checker)

    result = json.loads(
        provider.handle_tool_call(
            "team_memory_add",
            {
                "content": "任何时候都应该表明，我们是闻川网络科技公司。",
                "memory_type": "fact",
            },
        )
    )

    assert result["success"] is True
    assert result["notice"] == "团队记忆已创建：mem-team-1 - 任何时候都应该表明，我们是闻川网络科技公司。"
    assert checker.calls[0]["action"] == "memory.team.write"
    assert http_client.calls[0] == {
        "path": "/v1/memory",
        "json": {
            "org_id": "org-1",
            "scope": "team_shared",
            "team_id": "team-1",
            "project_id": "project-1",
            "created_by_member_id": "alice",
            "status": "active",
            "source_type": "admin_created",
            "content": "任何时候都应该表明，我们是闻川网络科技公司。",
            "memory_type": "fact",
            "sensitivity": "normal",
        },
        "headers": {"Authorization": "Bearer token-1"},
    }


def test_team_memory_add_normalizes_model_supplied_type_and_sensitivity_aliases():
    http_client = FakeTeamCloudHttpClient()
    http_client.responses["/v1/memory"] = {"id": "mem-team-2", "content": "闻川网络科技公司成立于2016年。"}
    provider = _provider(http_client=http_client)

    result = json.loads(
        provider.handle_tool_call(
            "team_memory_add",
            {
                "content": "闻川网络科技公司成立于2016年。",
                "memory_type": "company_info",
                "sensitivity": "public",
            },
        )
    )

    assert result["success"] is True
    assert http_client.calls[0]["json"]["memory_type"] == "fact"
    assert http_client.calls[0]["json"]["sensitivity"] == "normal"


def test_team_memory_add_defaults_unknown_sensitivity_to_normal():
    http_client = FakeTeamCloudHttpClient()
    provider = _provider(http_client=http_client)

    json.loads(
        provider.handle_tool_call(
            "team_memory_add",
            {
                "content": "闻川网络科技公司成立于2016年。",
                "memory_type": "general",
                "sensitivity": "internal",
            },
        )
    )

    assert http_client.calls[0]["json"]["memory_type"] == "fact"
    assert http_client.calls[0]["json"]["sensitivity"] == "normal"


def test_team_memory_propose_tool_returns_extraction_notice_with_memory_id():
    http_client = FakeTeamCloudHttpClient()
    http_client.responses["/v1/memory"] = {"id": "mem-auto-1", "content": "发布必须先完成回滚预案。"}
    checker = FixedPermissionChecker(True)
    provider = _provider(http_client=http_client, permission_checker=checker)

    result = json.loads(
        provider.handle_tool_call(
            "team_memory_propose",
            {"content": "发布必须先完成回滚预案。", "memory_type": "procedure"},
        )
    )

    assert result["success"] is True
    assert result["notice"] == "团队记忆已抽取：mem-auto-1 - 发布必须先完成回滚预案。"


def test_team_memory_propose_normalizes_model_supplied_fields():
    http_client = FakeTeamCloudHttpClient()
    provider = _provider(http_client=http_client)

    json.loads(
        provider.handle_tool_call(
            "team_memory_propose",
            {
                "content": "闻川网络科技公司成立于2016年。",
                "memory_type": "company_info",
                "sensitivity": "public",
            },
        )
    )

    assert http_client.calls[0]["json"]["memory_type"] == "fact"
    assert http_client.calls[0]["json"]["sensitivity"] == "normal"


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
