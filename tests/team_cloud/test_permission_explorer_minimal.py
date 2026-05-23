from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient


WEB_SHELL = Path("deploy/team-cloud/web-shell/index.html")


def test_permission_explain_api_returns_decision_and_cache_key():
    from team_cloud.api import create_app
    from team_cloud.authz.spicedb import PermissionDecision, ResourceRef, SubjectRef

    class FakeAuthzClient:
        def check(self, *, subject, resource, action=None, permission=None, consistency=None):
            assert subject == SubjectRef("user", "alice")
            assert resource == ResourceRef("organization", "hermes-labs")
            assert action is None
            assert permission == "manage_members"
            return PermissionDecision(
                allowed=True,
                reason="allowed",
                subject=subject,
                resource=resource,
                permission="manage_members",
            )

    client = TestClient(create_app(authz_client=FakeAuthzClient(), oidc_client=object()))

    response = client.get(
        "/api/authz/explain",
        params={
            "subject_type": "user",
            "subject_id": "alice",
            "resource_type": "organization",
            "resource_id": "hermes-labs",
            "permission": "manage_members",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "allowed": True,
        "reason": "allowed",
        "subject": "user:alice",
        "resource": "organization:hermes-labs",
        "permission": "manage_members",
        "cache_key": "user:alice|organization:hermes-labs|manage_members",
        "deny_reasons": [],
        "relationship_paths": [],
        "recent_relationship_changes": [],
    }


def test_permission_explain_api_fails_closed_when_authz_is_unavailable():
    from team_cloud.api import create_app

    class BrokenAuthzClient:
        def check(self, **_kwargs):
            raise RuntimeError("spicedb unavailable")

    client = TestClient(create_app(authz_client=BrokenAuthzClient(), oidc_client=object()))

    response = client.get(
        "/api/authz/explain",
        params={
            "subject_type": "user",
            "subject_id": "alice",
            "resource_type": "organization",
            "resource_id": "hermes-labs",
            "permission": "manage_members",
        },
    )

    assert response.status_code == 200
    assert response.json()["allowed"] is False
    assert response.json()["reason"] == "authorization_unavailable"
    assert response.json()["cache_key"] == "user:alice|organization:hermes-labs|manage_members"
    assert response.json()["deny_reasons"] == [
        "authorization_unavailable",
        "no_applied_relationship_path",
    ]


def test_web_permission_explorer_has_form_result_and_api_wiring():
    html = WEB_SHELL.read_text(encoding="utf-8")

    assert 'data-admin-tab="permission"' in html
    assert 'id="permission-panel"' in html
    assert 'id="permission-explain-form"' in html
    assert 'id="permission-subject-type"' in html
    assert 'id="permission-subject-id"' in html
    assert 'id="permission-resource-type"' in html
    assert 'id="permission-resource-id"' in html
    assert 'id="permission-action"' in html
    assert 'id="permission-name"' in html
    assert 'id="permission-decision"' in html
    assert 'id="permission-deny-reasons"' in html
    assert 'id="permission-relationship-paths"' in html
    assert 'id="permission-recent-changes"' in html
    assert 'id="permission-error"' in html
    assert "/api/authz/explain" in html
    assert "explainPermission" in html
    assert "renderPermissionDecision" in html
    assert "renderPermissionList" in html
