from __future__ import annotations

from fastapi.testclient import TestClient


def _review_client():
    from team_cloud.api import create_app
    from team_cloud.audit import InMemoryAuditLog
    from team_cloud.memory.extraction import InMemoryMemoryObservationRepository
    from team_cloud.memory.review import InMemoryMemoryReviewService
    from team_cloud.memory.service import InMemoryMemoryService

    memory_service = InMemoryMemoryService()
    review_repository = InMemoryMemoryObservationRepository()
    audit_log = InMemoryAuditLog()
    review_service = InMemoryMemoryReviewService(
        review_repository=review_repository,
        memory_service=memory_service,
        audit_log=audit_log,
    )
    client = TestClient(
        create_app(
            memory_review_service=review_service,
            oidc_client=object(),
        )
    )
    return client, memory_service, review_repository, audit_log


def _seed_review_item(memory_service, review_repository):
    memory = memory_service.create_memory(
        {
            "org_id": "org-1",
            "scope": "team_shared",
            "team_id": "team-1",
            "project_id": "project-1",
            "content": "Draft team memory.",
            "memory_type": "fact",
        }
    )
    review_item = review_repository.create_review_item(
        org_id="org-1",
        memory_id=memory["id"],
        proposed_scope="team_shared",
        reviewer_member_id=None,
        review_kind="team_candidate",
        candidate_payload={"content": memory["content"]},
        confidence=0.82,
    )
    return memory, review_item


def test_review_queue_api_lists_pending_items_by_org_and_kind():
    client, memory_service, review_repository, _audit_log = _review_client()
    _memory, review_item = _seed_review_item(memory_service, review_repository)

    response = client.get(
        "/v1/memory/review",
        params={"org_id": "org-1", "review_kind": "team_candidate"},
    )

    assert response.status_code == 200
    assert response.json()["items"][0]["id"] == review_item.id
    assert response.json()["items"][0]["status"] == "pending"
    assert response.json()["items"][0]["confidence"] == 0.82


def test_review_queue_api_approves_with_edit_before_approve_and_audits():
    client, memory_service, review_repository, audit_log = _review_client()
    memory, review_item = _seed_review_item(memory_service, review_repository)

    response = client.post(
        f"/v1/memory/review/{review_item.id}/approve",
        json={
            "actor_member_id": "reviewer-1",
            "content": "Edited team memory.",
            "memory_type": "procedure",
            "sensitivity": "normal",
        },
    )

    assert response.status_code == 200
    assert response.json()["review_item"]["status"] == "approved"
    assert response.json()["review_item"]["reviewer_member_id"] == "reviewer-1"
    assert response.json()["memory"]["id"] == memory["id"]
    assert response.json()["memory"]["status"] == "active"
    assert response.json()["memory"]["content"] == "Edited team memory."
    assert response.json()["memory"]["memory_type"] == "procedure"
    assert response.json()["memory"]["version"] == 2
    assert audit_log.events[-1]["action"] == "memory.review.approved"
    assert audit_log.events[-1]["actor_member_id"] == "reviewer-1"
    assert audit_log.events[-1]["metadata"]["edited"] is True


def test_review_queue_api_rejects_candidate_and_audits_reason():
    client, memory_service, review_repository, audit_log = _review_client()
    memory, review_item = _seed_review_item(memory_service, review_repository)

    response = client.post(
        f"/v1/memory/review/{review_item.id}/reject",
        json={
            "actor_member_id": "reviewer-1",
            "reason": "too vague",
        },
    )

    assert response.status_code == 200
    assert response.json()["review_item"]["status"] == "rejected"
    assert response.json()["review_item"]["reason"] == "too vague"
    assert response.json()["memory"]["id"] == memory["id"]
    assert response.json()["memory"]["status"] == "rejected"
    assert audit_log.events[-1]["action"] == "memory.review.rejected"
    assert audit_log.events[-1]["decision"] == "rejected"
    assert audit_log.events[-1]["metadata"]["reason"] == "too vague"
