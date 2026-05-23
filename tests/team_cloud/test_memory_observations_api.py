from __future__ import annotations

from fastapi.testclient import TestClient


def _client():
    from team_cloud.api import create_app
    from team_cloud.memory.extraction import InMemoryMemoryObservationRepository

    repository = InMemoryMemoryObservationRepository()
    return (
        TestClient(
            create_app(
                memory_observation_repository=repository,
                oidc_client=object(),
            )
        ),
        repository,
    )


def test_memory_observations_api_records_turn_metadata_and_tool_summaries():
    client, repository = _client()

    created = client.post(
        "/v1/memory/observations",
        json={
            "org_id": "org-1",
            "session_id": "session-1",
            "member_id": "alice",
            "team_id": "team-1",
            "project_id": "project-1",
            "observation": {
                "source": "hermes_turn",
                "messages": [
                    {"role": "user", "content": "remember this"},
                    {"role": "assistant", "content": "noted"},
                ],
                "turn_metadata": {
                    "run_id": "run-1",
                    "model": "test-model",
                    "turn_number": 3,
                },
                "tool_summaries": [
                    {
                        "name": "team_memory_search",
                        "status": "success",
                        "memory_ids": ["mem-1"],
                    }
                ],
            },
        },
    )

    assert created.status_code == 201
    body = created.json()
    assert body["status"] == "pending"
    stored = repository.observations[body["id"]]
    assert stored.org_id == "org-1"
    assert stored.session_id == "session-1"
    assert stored.member_id == "alice"
    assert stored.team_id == "team-1"
    assert stored.project_id == "project-1"
    assert stored.observation["turn_metadata"] == {
        "run_id": "run-1",
        "model": "test-model",
        "turn_number": 3,
    }
    assert stored.observation["tool_summaries"] == [
        {
            "name": "team_memory_search",
            "status": "success",
            "memory_ids": ["mem-1"],
        }
    ]
    assert stored.observation["context"] == {
        "org_id": "org-1",
        "session_id": "session-1",
        "member_id": "alice",
        "team_id": "team-1",
        "project_id": "project-1",
    }


def test_memory_observations_api_rejects_context_fence_mismatch():
    client, repository = _client()

    response = client.post(
        "/v1/memory/observations",
        json={
            "org_id": "org-1",
            "session_id": "session-1",
            "member_id": "alice",
            "team_id": "team-1",
            "observation": {
                "source": "hermes_turn",
                "messages": [],
                "context": {"member_id": "bob"},
            },
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "observation_context_mismatch: member_id"
    assert repository.observations == {}
