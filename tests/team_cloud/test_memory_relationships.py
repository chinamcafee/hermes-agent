from __future__ import annotations

from fastapi.testclient import TestClient


def test_personal_memory_create_enqueues_owner_relationship():
    from team_cloud.api import create_app
    from team_cloud.authz.outbox import InMemoryRelationshipOutboxRepository
    from team_cloud.memory.relationships import MemoryRelationshipService
    from team_cloud.memory.service import InMemoryMemoryService

    repository = InMemoryRelationshipOutboxRepository()
    relationship_service = MemoryRelationshipService(outbox_repository=repository)
    memory_service = InMemoryMemoryService(
        relationship_service=relationship_service,
    )
    client = TestClient(create_app(memory_service=memory_service, oidc_client=object()))

    created = client.post(
        "/v1/memory",
        json={
            "org_id": "org-1",
            "scope": "personal",
            "subject_member_id": "alice",
            "content": "Alice uses deterministic tests.",
        },
    )
    duplicate = client.post(
        "/v1/memory",
        json={
            "org_id": "org-1",
            "scope": "personal",
            "subject_member_id": "alice",
            "content": "A second personal memory.",
        },
    )

    assert created.status_code == 201
    assert duplicate.status_code == 201
    first_item = next(
        item
        for item in repository.items.values()
        if item.aggregate_id == created.json()["id"]
    )
    assert first_item.aggregate_type == "memory"
    assert first_item.operation == "touch"
    assert first_item.relationships == (
        f"memory:{created.json()['id']}#owner@user:alice",
    )
    assert first_item.status == "pending"


def test_team_shared_memory_create_enqueues_parent_and_reviewer_relationships_idempotently():
    from team_cloud.authz.outbox import InMemoryRelationshipOutboxRepository
    from team_cloud.memory.relationships import MemoryRelationshipService

    repository = InMemoryRelationshipOutboxRepository()
    relationship_service = MemoryRelationshipService(outbox_repository=repository)
    memory = {
        "id": "mem-42",
        "org_id": "org-1",
        "scope": "team_shared",
        "team_id": "team-1",
        "project_id": "project-1",
    }

    first = relationship_service.enqueue_memory_relationships(
        memory,
        reviewer_member_ids=["reviewer-1", "reviewer-2"],
    )
    second = relationship_service.enqueue_memory_relationships(
        memory,
        reviewer_member_ids=["reviewer-2", "reviewer-1"],
    )

    assert first.id == second.id
    assert len(repository.items) == 1
    assert first.aggregate_type == "memory"
    assert first.aggregate_id == "mem-42"
    assert first.relationships == (
        "memory:mem-42#parent_project@project:project-1",
        "memory:mem-42#parent_team@team:team-1",
        "memory:mem-42#curator@user:reviewer-1",
        "memory:mem-42#curator@user:reviewer-2",
    )


def test_memory_relationship_planner_rejects_incomplete_scope_context():
    from team_cloud.authz.outbox import InMemoryRelationshipOutboxRepository
    from team_cloud.memory.relationships import MemoryRelationshipService

    service = MemoryRelationshipService(
        outbox_repository=InMemoryRelationshipOutboxRepository(),
    )

    try:
        service.enqueue_memory_relationships(
            {"id": "mem-1", "org_id": "org-1", "scope": "personal"},
        )
    except ValueError as exc:
        assert str(exc) == "personal memory relationship requires subject_member_id"
    else:
        raise AssertionError("expected missing personal subject to be rejected")

    try:
        service.enqueue_memory_relationships(
            {"id": "mem-2", "org_id": "org-1", "scope": "team_shared"},
        )
    except ValueError as exc:
        assert str(exc) == "team_shared memory relationship requires team_id"
    else:
        raise AssertionError("expected missing team parent to be rejected")
