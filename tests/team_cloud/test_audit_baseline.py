from __future__ import annotations

from fastapi.testclient import TestClient


def test_audit_log_records_and_filters_events():
    from team_cloud.audit import InMemoryAuditLog

    audit = InMemoryAuditLog()
    audit.record(
        action="member.invited",
        org_id="org-1",
        actor_type="human",
        resource_type="member",
        resource_id="member-1",
        decision="recorded",
        metadata={"email": "alice@example.com"},
    )
    audit.record(
        action="member.disabled",
        org_id="org-1",
        actor_type="human",
        resource_type="member",
        resource_id="member-1",
        decision="recorded",
    )

    assert [event["action"] for event in audit.query(org_id="org-1")] == [
        "member.invited",
        "member.disabled",
    ]
    assert [event["action"] for event in audit.query(action="member.disabled")] == [
        "member.disabled"
    ]


def test_audit_middleware_records_api_requests():
    from team_cloud.admin.organizations import InMemoryOrganizationService
    from team_cloud.api import create_app
    from team_cloud.audit import InMemoryAuditLog
    from team_cloud.authz.outbox import InMemoryRelationshipOutboxRepository

    audit = InMemoryAuditLog()
    service = InMemoryOrganizationService(
        outbox_repository=InMemoryRelationshipOutboxRepository()
    )
    client = TestClient(
        create_app(
            audit_log=audit,
            organization_service=service,
            oidc_client=object(),
        )
    )

    response = client.post(
        "/api/organizations",
        json={"slug": "hermes-labs", "name": "Hermes Labs"},
    )

    assert response.status_code == 201
    assert audit.events[-1]["action"] == "http.request"
    assert audit.events[-1]["resource_type"] == "api_route"
    assert audit.events[-1]["decision"] == "allowed"
    assert audit.events[-1]["metadata"]["method"] == "POST"
    assert audit.events[-1]["metadata"]["path"] == "/api/organizations"
    assert audit.events[-1]["metadata"]["status_code"] == 201


def test_audit_query_api_returns_filtered_events_without_recording_itself():
    from team_cloud.api import create_app
    from team_cloud.audit import InMemoryAuditLog

    audit = InMemoryAuditLog()
    audit.record(action="member.invited", org_id="org-1", resource_type="member")
    audit.record(action="member.disabled", org_id="org-1", resource_type="member")
    client = TestClient(create_app(audit_log=audit, oidc_client=object()))

    response = client.get("/api/audit/events", params={"action": "member.disabled"})

    assert response.status_code == 200
    assert response.json()["items"] == [audit.events[-1]]
    assert len(audit.events) == 2
