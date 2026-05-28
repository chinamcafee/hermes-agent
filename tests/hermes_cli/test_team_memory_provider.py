from __future__ import annotations


class FakeTeamCloudHttpClient:
    def __init__(self):
        self.calls = []
        self.responses = {}

    def post_json(self, path: str, *, json, headers):
        self.calls.append({"path": path, "json": json, "headers": headers})
        return self.responses.get(path, {})


def _context():
    from agent.team_memory_provider import TeamContext

    return TeamContext(
        org_id="org-1",
        team_id="team-1",
        project_id="project-1",
        member_id="alice",
    )


def test_team_memory_provider_is_inactive_when_missing_config():
    from agent.team_memory_provider import TeamMemoryProvider, TeamMemoryProviderConfig

    http_client = FakeTeamCloudHttpClient()
    provider = TeamMemoryProvider(
        config=TeamMemoryProviderConfig(team_cloud_url="", service_token="", team_context=None),
        http_client=http_client,
    )

    provider.initialize("session-1")

    assert provider.name == "team_cloud"
    assert not provider.is_available()
    assert provider.prefetch("release plan", session_id="session-1") == ""
    provider.sync_turn("hello", "hi", session_id="session-1")
    assert http_client.calls == []


def test_team_memory_provider_prefetch_calls_team_cloud_and_formats_context():
    from agent.team_memory_provider import TeamMemoryProvider, TeamMemoryProviderConfig

    http_client = FakeTeamCloudHttpClient()
    http_client.responses["/v1/memory/prefetch"] = {
        "partitions": [
            {
                "scope": "team_shared",
                "items": [
                    {
                        "id": "team-1",
                        "scope": "team_shared",
                        "memory_type": "procedure",
                        "sensitivity": "normal",
                        "content": "Release checklist lives in docs/releases.md.",
                    }
                ],
            },
        ],
        "memory_ids": ["team-1"],
    }
    provider = TeamMemoryProvider(
        config=TeamMemoryProviderConfig(
            team_cloud_url="https://team-cloud.example",
            service_token="token-1",
            team_context=_context(),
        ),
        http_client=http_client,
    )
    provider.initialize("session-1")

    context_block = provider.prefetch("release plan", session_id="session-1")

    assert "Team Cloud memory" in context_block
    assert "personal-1" not in context_block
    assert "team-1" in context_block
    assert "Release checklist lives in docs/releases.md." in context_block
    assert http_client.calls[0] == {
        "path": "/v1/memory/prefetch",
        "json": {
            "query": "release plan",
            "org_id": "org-1",
            "member_id": "alice",
            "team_id": "team-1",
            "project_id": "project-1",
            "limit": 8,
            "include_personal": False,
        },
        "headers": {"Authorization": "Bearer token-1"},
    }


def test_team_memory_provider_sync_turn_posts_observation():
    from agent.team_memory_provider import TeamMemoryProvider, TeamMemoryProviderConfig

    http_client = FakeTeamCloudHttpClient()
    provider = TeamMemoryProvider(
        config=TeamMemoryProviderConfig(
            team_cloud_url="https://team-cloud.example",
            service_token="token-1",
            team_context=_context(),
        ),
        http_client=http_client,
    )
    provider.initialize("init-session")

    provider.sync_turn("remember deploys", "noted", session_id="session-1")

    assert http_client.calls == [
        {
            "path": "/v1/memory/observations",
            "json": {
                "org_id": "org-1",
                "session_id": "session-1",
                "member_id": "alice",
                "team_id": "team-1",
                "project_id": "project-1",
                "observation": {
                    "source": "hermes_turn",
                    "messages": [
                        {"role": "user", "content": "remember deploys"},
                        {"role": "assistant", "content": "noted"},
                    ],
                },
            },
            "headers": {"Authorization": "Bearer token-1"},
        }
    ]


def test_team_memory_provider_sync_turn_includes_metadata_and_tool_summaries():
    from agent.team_memory_provider import TeamMemoryProvider, TeamMemoryProviderConfig

    http_client = FakeTeamCloudHttpClient()
    provider = TeamMemoryProvider(
        config=TeamMemoryProviderConfig(
            team_cloud_url="https://team-cloud.example",
            service_token="token-1",
            team_context=_context(),
        ),
        http_client=http_client,
    )

    provider.sync_turn(
        "search memory",
        "found one",
        session_id="session-1",
        turn_metadata={"run_id": "run-1", "turn_number": 2},
        tool_summaries=[
            {
                "name": "team_memory_search",
                "status": "success",
                "memory_ids": ["mem-1"],
            }
        ],
    )

    observation = http_client.calls[0]["json"]["observation"]
    assert observation["turn_metadata"] == {"run_id": "run-1", "turn_number": 2}
    assert observation["tool_summaries"] == [
        {
            "name": "team_memory_search",
            "status": "success",
            "memory_ids": ["mem-1"],
        }
    ]
