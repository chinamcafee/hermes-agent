from __future__ import annotations

from fastapi.testclient import TestClient


class RejectingOIDCClient:
    def verify_id_token(self, token: str, **_kwargs):
        from team_cloud.auth.oidc import OIDCVerificationError

        raise OIDCVerificationError(f"forged token: {token}")

    def authorization_url(self, **_kwargs):
        return "http://casdoor.local/login/oauth/authorize"


class OrgScopedAuthzClient:
    def __init__(self, *, allowed_org_id: str):
        self.allowed_org_id = allowed_org_id
        self.calls = []

    def check(self, **kwargs):
        from team_cloud.authz.spicedb import PermissionDecision

        self.calls.append(kwargs)
        allowed = kwargs["resource"].id == self.allowed_org_id
        return PermissionDecision(
            allowed=allowed,
            reason="allowed" if allowed else "denied",
            subject=kwargs["subject"],
            resource=kwargs["resource"],
            permission=kwargs.get("permission") or "manage_members",
        )


def test_forged_bearer_token_is_rejected_without_token_leakage():
    from team_cloud.api import create_app
    from team_cloud.config import TeamCloudConfig

    config = TeamCloudConfig(
        jwt_issuer="http://casdoor.local",
        casdoor_base_url="http://casdoor.local",
        casdoor_client_id="team-api",
    )
    client = TestClient(
        create_app(
            config,
            oidc_client=RejectingOIDCClient(),
            enable_jwt_middleware=True,
        )
    )

    response = client.get(
        "/api/whoami",
        headers={"Authorization": "Bearer forged.jwt.value"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "invalid_token"
    assert "forged.jwt.value" not in response.text


def test_disabled_member_cannot_reach_protected_api():
    from team_cloud.api import create_app
    from team_cloud.config import TeamCloudConfig

    class ActiveOIDCClient:
        def verify_id_token(self, token: str, **_kwargs):
            return {"sub": "alice", "email": "alice@example.com", "name": "Alice"}

    config = TeamCloudConfig(
        jwt_issuer="http://casdoor.local",
        casdoor_base_url="http://casdoor.local",
        casdoor_client_id="team-api",
    )
    client = TestClient(
        create_app(
            config,
            oidc_client=ActiveOIDCClient(),
            enable_jwt_middleware=True,
            member_status_resolver=lambda _claims: "suspended",
        )
    )

    response = client.get(
        "/api/whoami",
        headers={"Authorization": "Bearer valid-token"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "member_not_active"


def test_cross_org_member_invite_is_rejected_by_authz_gate():
    from team_cloud.admin.organizations import InMemoryOrganizationService
    from team_cloud.api import create_app
    from team_cloud.authz.outbox import InMemoryRelationshipOutboxRepository
    from team_cloud.authz.spicedb import SubjectRef

    outbox = InMemoryRelationshipOutboxRepository()
    service = InMemoryOrganizationService(outbox_repository=outbox)
    authz_client = OrgScopedAuthzClient(allowed_org_id="org-a")
    client = TestClient(
        create_app(
            organization_service=service,
            oidc_client=object(),
            authz_client=authz_client,
            enable_authz_middleware=True,
            authz_subject_resolver=lambda _request: SubjectRef("user", "alice"),
        )
    )
    client.post("/api/organizations", json={"slug": "org-a", "name": "Org A"})
    client.post("/api/organizations", json={"slug": "org-b", "name": "Org B"})

    allowed = client.post(
        "/api/organizations/org-a/members/invite",
        json={
            "email": "alice@example.com",
            "display_name": "Alice",
            "user_id": "alice",
            "role": "member",
        },
    )
    denied = client.post(
        "/api/organizations/org-b/members/invite",
        json={
            "email": "bob@example.com",
            "display_name": "Bob",
            "user_id": "bob",
            "role": "member",
        },
    )

    assert allowed.status_code == 201
    assert denied.status_code == 403
    assert denied.json()["detail"] == "permission_denied"
    assert ("org-b", "org-b:bob") not in service.members
    assert [call["resource"].id for call in authz_client.calls] == ["org-a", "org-b"]
