from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient


NOW = datetime(2026, 5, 22, 19, 0, tzinfo=UTC)


class FailingSpiceDBTransport:
    def check_permission(self, **_kwargs):
        raise RuntimeError("spicedb unavailable")

    def lookup_resources(self, **_kwargs):
        raise RuntimeError("spicedb unavailable")

    def write_relationships(self, **_kwargs):
        raise RuntimeError("spicedb unavailable")


class AllowingAuthzClient:
    def __init__(self):
        self.calls = []

    def check(self, **kwargs):
        from team_cloud.authz.spicedb import PermissionDecision

        self.calls.append(kwargs)
        return PermissionDecision(
            allowed=True,
            reason="allowed",
            subject=kwargs["subject"],
            resource=kwargs["resource"],
            permission=kwargs.get("permission") or "manage_members",
        )


def _spicedb_outage_client():
    from team_cloud.authz.spicedb import SpiceDBClient

    return SpiceDBClient(transport=FailingSpiceDBTransport(), fail_closed=True)


def test_admin_authz_middleware_reports_spicedb_outage_as_unavailable():
    from team_cloud.admin.organizations import InMemoryOrganizationService
    from team_cloud.api import create_app
    from team_cloud.authz.outbox import InMemoryRelationshipOutboxRepository
    from team_cloud.authz.spicedb import SubjectRef

    outbox = InMemoryRelationshipOutboxRepository()
    service = InMemoryOrganizationService(outbox_repository=outbox)
    client = TestClient(
        create_app(
            organization_service=service,
            oidc_client=object(),
            authz_client=_spicedb_outage_client(),
            enable_authz_middleware=True,
            authz_subject_resolver=lambda _request: SubjectRef("user", "alice"),
        )
    )
    client.post("/api/organizations", json={"slug": "org-a", "name": "Org A"})

    response = client.post(
        "/api/organizations/org-a/members/invite",
        json={
            "email": "alice@example.com",
            "display_name": "Alice",
            "user_id": "alice",
            "role": "member",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "authorization_unavailable"
    assert service.members == {}


def test_chat_run_reports_spicedb_outage_as_unavailable_before_creation():
    from team_cloud.api import create_app

    client = TestClient(
        create_app(
            oidc_client=object(),
            authz_client=_spicedb_outage_client(),
        )
    )

    response = client.post(
        "/api/chat/runs",
        json={
            "org_id": "org-1",
            "team_id": "team-1",
            "project_id": "project-1",
            "member_id": "alice",
            "message": "hello",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "authorization_unavailable"


def test_high_risk_tool_policy_fails_closed_on_spicedb_outage():
    from team_cloud.tool_policy import TeamToolPolicyHook

    hook = TeamToolPolicyHook(authz_client=_spicedb_outage_client())

    result = hook.pre_tool_call(
        tool_name="terminal",
        args={"command": "pytest"},
        team_context={
            "org_id": "org-1",
            "team_id": "team-1",
            "project_id": "project-1",
            "member_id": "alice",
        },
    )

    assert result["action"] == "block"
    assert result["metadata"]["reason"] == "authorization_unavailable"
    assert result["metadata"]["authz_reason"] == "spicedb_error"


def test_outbox_fail_closed_status_distinguishes_lag_and_dead_letter():
    from team_cloud.authz.outbox import (
        InMemoryRelationshipOutboxRepository,
        RelationshipOutboxService,
    )

    repository = InMemoryRelationshipOutboxRepository()
    service = RelationshipOutboxService(repository)
    lagging = service.enqueue(
        org_id="org-1",
        aggregate_type="project",
        aggregate_id="project-1",
        operation="touch",
        relationships=["project:project-1#member@user:alice"],
        created_at=NOW - timedelta(minutes=15),
    )

    lag_status = service.fail_closed_status(
        aggregate_type="project",
        aggregate_id="project-1",
        now=NOW,
        lag_after=timedelta(minutes=5),
    )

    assert lag_status["blocked"] is True
    assert lag_status["reasons"] == (
        "relationship_outbox_pending",
        "relationship_outbox_lag",
    )
    assert lag_status["items"][0]["id"] == lagging.id
    assert lag_status["items"][0]["age_seconds"] == 900

    repository.mark_failed(
        lagging.id,
        attempts=5,
        error="spicedb write failed",
        dead_letter=True,
    )

    dead_letter_status = service.fail_closed_status(
        aggregate_type="project",
        aggregate_id="project-1",
        now=NOW,
        lag_after=timedelta(minutes=5),
    )

    assert dead_letter_status["blocked"] is True
    assert dead_letter_status["reasons"] == ("relationship_outbox_dead_letter",)
    assert dead_letter_status["items"][0]["status"] == "dead_letter"


def test_outbox_dead_letter_blocks_related_resource_before_authz_check():
    from fastapi import FastAPI

    from team_cloud.authz.middleware import RoutePermissionRule, install_authz_middleware
    from team_cloud.authz.outbox import (
        InMemoryRelationshipOutboxRepository,
        RelationshipOutboxService,
    )
    from team_cloud.authz.spicedb import SubjectRef

    repository = InMemoryRelationshipOutboxRepository()
    outbox_service = RelationshipOutboxService(repository)
    item = outbox_service.enqueue(
        org_id="org-1",
        aggregate_type="project",
        aggregate_id="project-1",
        operation="touch",
        relationships=["project:project-1#member@user:alice"],
        created_at=NOW,
    )
    repository.mark_failed(
        item.id,
        attempts=5,
        error="spicedb write failed",
        dead_letter=True,
    )
    authz_client = AllowingAuthzClient()
    app = FastAPI()

    @app.get("/api/projects/{project_id}/run")
    def run_project(project_id: str):
        return {"project_id": project_id}

    install_authz_middleware(
        app,
        authz_client=authz_client,
        route_permissions=[
            RoutePermissionRule(
                method="GET",
                path_template="/api/projects/{project_id}/run",
                resource_type="project",
                resource_id_param="project_id",
                action="chat.run",
            )
        ],
        subject_resolver=lambda _request: SubjectRef("user", "alice"),
        outbox_pending=lambda resource_type, resource_id: outbox_service.requires_fail_closed(
            aggregate_type=resource_type,
            aggregate_id=resource_id,
        ),
    )

    response = TestClient(app).get("/api/projects/project-1/run")

    assert response.status_code == 403
    assert response.json()["detail"] == "authorization_pending_relationship_sync"
    assert authz_client.calls == []
