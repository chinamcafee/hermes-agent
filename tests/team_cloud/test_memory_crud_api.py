from __future__ import annotations

from fastapi.testclient import TestClient


def _client():
    from team_cloud.api import create_app
    from team_cloud.memory.service import InMemoryMemoryService

    service = InMemoryMemoryService()
    return TestClient(create_app(memory_service=service, oidc_client=object())), service


def test_memory_api_creates_and_lists_personal_memory():
    client, service = _client()

    created = client.post(
        "/v1/memory",
        json={
            "org_id": "org-1",
            "scope": "personal",
            "subject_member_id": "alice",
            "content": "Alice prefers deterministic tests.",
            "memory_type": "preference",
        },
    )
    listed = client.get(
        "/v1/memory",
        params={"org_id": "org-1", "scope": "personal", "status": "active"},
    )

    assert created.status_code == 201
    assert created.json()["status"] == "active"
    assert created.json()["checksum_sha256"]
    assert listed.status_code == 200
    assert listed.json()["items"] == [created.json()]
    assert [event["event_type"] for event in service.events] == ["create"]


def test_memory_api_updates_version_and_writes_event():
    client, service = _client()
    memory = client.post(
        "/v1/memory",
        json={
            "org_id": "org-1",
            "scope": "personal",
            "subject_member_id": "alice",
            "content": "Old content",
        },
    ).json()

    updated = client.patch(
        f"/v1/memory/{memory['id']}",
        json={"content": "New content", "actor_member_id": "alice"},
    )

    assert updated.status_code == 200
    assert updated.json()["version"] == 2
    assert updated.json()["content"] == "New content"
    assert [event["event_type"] for event in service.events] == ["create", "update"]


def test_memory_api_soft_deletes_and_restores_memory():
    client, service = _client()
    memory = client.post(
        "/v1/memory",
        json={
            "org_id": "org-1",
            "scope": "personal",
            "subject_member_id": "alice",
            "content": "Temporary content",
        },
    ).json()

    deleted = client.delete(f"/v1/memory/{memory['id']}", params={"actor_member_id": "alice"})
    restored = client.post(
        f"/v1/memory/{memory['id']}/restore",
        json={"actor_member_id": "alice"},
    )

    assert deleted.status_code == 200
    assert deleted.json()["status"] == "deleted"
    assert restored.status_code == 200
    assert restored.json()["status"] == "active"
    assert [event["event_type"] for event in service.events] == [
        "create",
        "delete",
        "restore",
    ]


def test_team_shared_memory_defaults_to_pending_review():
    client, _service = _client()

    created = client.post(
        "/v1/memory",
        json={
            "org_id": "org-1",
            "scope": "team_shared",
            "team_id": "team-1",
            "project_id": "project-1",
            "content": "Team shared candidate.",
            "memory_type": "fact",
        },
    )

    assert created.status_code == 201
    assert created.json()["status"] == "pending_review"
    assert created.json()["scope"] == "team_shared"
