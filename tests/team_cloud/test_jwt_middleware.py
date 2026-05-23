from __future__ import annotations

from fastapi.testclient import TestClient

from team_cloud.config import TeamCloudConfig


class FakeOIDCClient:
    def __init__(self, *, should_fail: bool = False):
        self.should_fail = should_fail

    def verify_id_token(self, token: str, **kwargs):
        if self.should_fail or token == "bad-token":
            from team_cloud.auth.oidc import OIDCVerificationError

            raise OIDCVerificationError("invalid token")
        return {
            "sub": "casdoor-user-1",
            "email": "admin@example.com",
            "name": "Admin",
            "iss": "http://casdoor.local",
            "aud": "team-api",
        }

    def authorization_url(self, **kwargs):
        return "http://casdoor.local/login/oauth/authorize"


def _config() -> TeamCloudConfig:
    return TeamCloudConfig(
        jwt_issuer="http://casdoor.local",
        casdoor_base_url="http://casdoor.local",
        casdoor_client_id="team-api",
    )


def _client(status: str = "active", oidc_client=None) -> TestClient:
    from team_cloud.api import create_app

    def member_status_resolver(claims):
        assert claims["sub"] == "casdoor-user-1"
        return status

    return TestClient(
        create_app(
            _config(),
            oidc_client=oidc_client or FakeOIDCClient(),
            enable_jwt_middleware=True,
            member_status_resolver=member_status_resolver,
        )
    )


def test_public_health_and_oidc_paths_skip_jwt_middleware():
    client = _client()

    assert client.get("/healthz").status_code == 200
    assert client.get(
        "/auth/oidc/authorize",
        params={"redirect_uri": "http://localhost:8780/auth/oidc/callback"},
    ).status_code == 200


def test_protected_api_requires_bearer_token():
    response = _client().get("/api/whoami")

    assert response.status_code == 401
    assert response.json()["detail"] == "missing_bearer_token"
    assert response.headers["www-authenticate"] == "Bearer"


def test_invalid_token_is_rejected():
    response = _client(oidc_client=FakeOIDCClient(should_fail=True)).get(
        "/api/whoami",
        headers={"Authorization": "Bearer bad-token"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "invalid_token"


def test_inactive_member_is_forbidden_fail_closed():
    response = _client(status="suspended").get(
        "/api/whoami",
        headers={"Authorization": "Bearer good-token"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "member_not_active"


def test_active_member_principal_reaches_api_without_token_leakage():
    response = _client().get(
        "/api/whoami",
        headers={"Authorization": "Bearer good-token"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["subject"] == "casdoor-user-1"
    assert payload["email"] == "admin@example.com"
    assert payload["member_status"] == "active"
    assert "good-token" not in response.text
