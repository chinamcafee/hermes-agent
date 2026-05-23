from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient


WEB_SHELL = Path("deploy/team-cloud/web-shell/index.html")


def _client():
    from team_cloud.admin.organizations import InMemoryOrganizationService
    from team_cloud.api import create_app
    from team_cloud.authz.outbox import InMemoryRelationshipOutboxRepository

    outbox_repository = InMemoryRelationshipOutboxRepository()
    service = InMemoryOrganizationService(outbox_repository=outbox_repository)
    app = create_app(
        organization_service=service,
        oidc_client=object(),
    )
    return TestClient(app)


def test_member_api_lists_members_for_selected_organization():
    client = _client()

    org = client.post(
        "/api/organizations",
        json={"slug": "hermes-labs", "name": "Hermes Labs"},
    ).json()
    alice = client.post(
        f"/api/organizations/{org['id']}/members/invite",
        json={
            "email": "alice@example.com",
            "display_name": "Alice",
            "user_id": "alice",
            "role": "admin",
        },
    ).json()
    bob = client.post(
        f"/api/organizations/{org['id']}/members/invite",
        json={
            "email": "bob@example.com",
            "display_name": "Bob",
            "user_id": "bob",
            "role": "member",
        },
    ).json()

    listed = client.get(f"/api/organizations/{org['id']}/members")

    assert listed.status_code == 200
    assert listed.json()["items"] == [alice, bob]


def test_web_admin_pages_expose_teams_members_roles_surfaces():
    html = WEB_SHELL.read_text(encoding="utf-8")

    assert 'data-admin-tab="teams"' in html
    assert 'data-admin-tab="members"' in html
    assert 'data-admin-tab="roles"' in html
    assert 'id="teams-panel"' in html
    assert 'id="members-panel"' in html
    assert 'id="roles-panel"' in html
    assert 'id="create-team-form"' in html
    assert 'id="invite-member-form"' in html
    assert 'id="member-role"' in html
    assert 'id="roles-table"' in html


def test_web_admin_pages_wire_org_scoped_api_and_error_states():
    html = WEB_SHELL.read_text(encoding="utf-8")

    assert "/api/organizations/${orgId}/teams" in html
    assert "/api/organizations/${orgId}/members" in html
    assert "/api/organizations/${orgId}/members/invite" in html
    assert "/api/organizations/${orgId}/members/${memberId}/disable" in html
    assert 'id="teams-error"' in html
    assert 'id="members-error"' in html
    assert 'id="roles-error"' in html
    assert "loadTeams" in html
    assert "loadMembers" in html
    assert "createTeam" in html
    assert "inviteMember" in html
    assert "disableMember" in html
    assert "renderRoles" in html
