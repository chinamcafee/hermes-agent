from __future__ import annotations

from fastapi.testclient import TestClient


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
    return TestClient(app), service, outbox_repository


def test_organization_api_creates_and_lists_organizations():
    client, _service, _outbox = _client()

    created = client.post(
        "/api/organizations",
        json={"slug": "hermes-labs", "name": "Hermes Labs"},
    )
    listed = client.get("/api/organizations")

    assert created.status_code == 201
    assert created.json()["slug"] == "hermes-labs"
    assert listed.status_code == 200
    assert listed.json()["items"] == [created.json()]


def test_team_api_creates_and_lists_teams_under_org():
    client, _service, _outbox = _client()

    org = client.post(
        "/api/organizations",
        json={"slug": "hermes-labs", "name": "Hermes Labs"},
    ).json()
    created = client.post(
        f"/api/organizations/{org['id']}/teams",
        json={"slug": "platform", "name": "Platform"},
    )
    listed = client.get(f"/api/organizations/{org['id']}/teams")

    assert created.status_code == 201
    assert created.json()["slug"] == "platform"
    assert listed.status_code == 200
    assert listed.json()["items"] == [created.json()]


def test_member_invite_and_disable_updates_status_and_relationship_outbox():
    client, _service, outbox = _client()

    org = client.post(
        "/api/organizations",
        json={"slug": "hermes-labs", "name": "Hermes Labs"},
    ).json()
    invited = client.post(
        f"/api/organizations/{org['id']}/members/invite",
        json={
            "email": "alice@example.com",
            "display_name": "Alice",
            "user_id": "alice",
            "role": "member",
        },
    )
    disabled = client.patch(
        f"/api/organizations/{org['id']}/members/{invited.json()['id']}/disable"
    )

    assert invited.status_code == 201
    assert invited.json()["status"] == "invited"
    assert disabled.status_code == 200
    assert disabled.json()["status"] == "suspended"
    outbox_items = list(outbox.items.values())
    assert outbox_items[-1].operation == "delete"
    assert outbox_items[-1].relationships == (
        f"organization:{org['id']}#member@user:alice",
    )


def test_admin_api_returns_404_for_unknown_org_or_member():
    client, _service, _outbox = _client()

    missing_team = client.post(
        "/api/organizations/missing-org/teams",
        json={"slug": "platform", "name": "Platform"},
    )
    missing_member = client.patch(
        "/api/organizations/missing-org/members/missing-member/disable"
    )

    assert missing_team.status_code == 404
    assert missing_team.json()["detail"] == "organization_not_found"
    assert missing_member.status_code == 404
    assert missing_member.json()["detail"] == "member_not_found"
