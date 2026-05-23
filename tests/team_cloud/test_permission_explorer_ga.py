from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient


NOW = datetime(2026, 5, 22, 17, 0, tzinfo=UTC)
WEB_SHELL = Path("deploy/team-cloud/web-shell/index.html")


def test_permission_explain_ga_includes_relationship_paths_and_recent_changes():
    from team_cloud.api import create_app
    from team_cloud.authz.outbox import InMemoryRelationshipOutboxRepository, RelationshipOutboxService
    from team_cloud.authz.spicedb import PermissionDecision

    repository = InMemoryRelationshipOutboxRepository()
    service = RelationshipOutboxService(repository)
    path_item = service.enqueue(
        org_id="org-1",
        aggregate_type="organization",
        aggregate_id="org-1",
        operation="touch",
        relationships=["organization:org-1#member@user:alice"],
        created_at=NOW - timedelta(minutes=5),
    )
    repository.mark_applied(path_item.id, processed_at=NOW - timedelta(minutes=4))
    service.enqueue(
        org_id="org-1",
        aggregate_type="organization",
        aggregate_id="org-1",
        operation="delete",
        relationships=["organization:org-1#guest@user:bob"],
        created_at=NOW - timedelta(minutes=1),
    )

    class FakeAuthzClient:
        def check(self, *, subject, resource, action=None, permission=None, consistency=None):
            return PermissionDecision(
                allowed=True,
                reason="allowed",
                subject=subject,
                resource=resource,
                permission=permission or "member",
            )

    client = TestClient(
        create_app(
            authz_client=FakeAuthzClient(),
            relationship_outbox_repository=repository,
            oidc_client=object(),
        )
    )

    response = client.get(
        "/api/authz/explain",
        params={
            "subject_type": "user",
            "subject_id": "alice",
            "resource_type": "organization",
            "resource_id": "org-1",
            "permission": "member",
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["allowed"] is True
    assert payload["deny_reasons"] == []
    assert payload["relationship_paths"] == [
        {
            "relationship": "organization:org-1#member@user:alice",
            "operation": "touch",
            "status": "applied",
            "aggregate_type": "organization",
            "aggregate_id": "org-1",
            "source": "relationship_outbox",
            "created_at": "2026-05-22T16:55:00+00:00",
            "processed_at": "2026-05-22T16:56:00+00:00",
        }
    ]
    assert [item["relationship"] for item in payload["recent_relationship_changes"]] == [
        "organization:org-1#guest@user:bob",
        "organization:org-1#member@user:alice",
    ]
    assert payload["recent_relationship_changes"][0]["status"] == "pending"


def test_permission_explain_ga_denied_response_mentions_pending_relationships():
    from team_cloud.api import create_app
    from team_cloud.authz.outbox import InMemoryRelationshipOutboxRepository, RelationshipOutboxService
    from team_cloud.authz.spicedb import PermissionDecision

    repository = InMemoryRelationshipOutboxRepository()
    RelationshipOutboxService(repository).enqueue(
        org_id="org-1",
        aggregate_type="organization",
        aggregate_id="org-1",
        operation="touch",
        relationships=["organization:org-1#member@user:alice"],
        created_at=NOW,
    )

    class FakeAuthzClient:
        def check(self, *, subject, resource, action=None, permission=None, consistency=None):
            return PermissionDecision(
                allowed=False,
                reason="denied",
                subject=subject,
                resource=resource,
                permission=permission or "member",
            )

    client = TestClient(
        create_app(
            authz_client=FakeAuthzClient(),
            relationship_outbox_repository=repository,
            oidc_client=object(),
        )
    )

    response = client.get(
        "/api/authz/explain",
        params={
            "subject_type": "user",
            "subject_id": "alice",
            "resource_type": "organization",
            "resource_id": "org-1",
            "permission": "member",
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["allowed"] is False
    assert payload["relationship_paths"] == []
    assert payload["deny_reasons"] == [
        "spicedb_denied",
        "relationship_outbox_pending",
        "no_applied_relationship_path",
    ]


def test_web_permission_explorer_ga_has_relationship_path_recent_change_and_deny_sections():
    html = WEB_SHELL.read_text(encoding="utf-8")

    assert 'id="permission-deny-reasons"' in html
    assert 'id="permission-relationship-paths"' in html
    assert 'id="permission-recent-changes"' in html
    assert "renderPermissionList" in html
    assert "relationship_paths" in html
    assert "recent_relationship_changes" in html
    assert "deny_reasons" in html
