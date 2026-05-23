from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from pydantic import SecretStr

from team_cloud.config import TeamCloudConfig


@dataclass(frozen=True)
class SigningKey:
    kid: str
    private_key: object
    jwk: dict[str, str]


def _b64url_uint(value: int) -> str:
    raw = value.to_bytes((value.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _signing_key(kid: str) -> SigningKey:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    numbers = private_key.public_key().public_numbers()
    jwk = {
        "kty": "RSA",
        "use": "sig",
        "alg": "RS256",
        "kid": kid,
        "n": _b64url_uint(numbers.n),
        "e": _b64url_uint(numbers.e),
    }
    return SigningKey(kid=kid, private_key=private_key, jwk=jwk)


def _id_token(key: SigningKey, *, audience: str = "team-api") -> str:
    now = int(time.time())
    return jwt.encode(
        {
            "iss": "http://casdoor.local",
            "sub": "casdoor-user-1",
            "aud": audience,
            "exp": now + 300,
            "nbf": now - 5,
            "iat": now,
            "email": "admin@example.com",
            "name": "Admin",
            "nonce": "nonce-123",
        },
        key.private_key,
        algorithm="RS256",
        headers={"kid": key.kid},
    )


def _config() -> TeamCloudConfig:
    return TeamCloudConfig(
        jwt_issuer="http://casdoor.local",
        casdoor_base_url="http://casdoor.local",
        casdoor_client_id="team-api",
        casdoor_client_secret=SecretStr("client-secret"),
    )


def _transport(keys: list[SigningKey]) -> httpx.MockTransport:
    calls = {"jwks": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/.well-known/openid-configuration":
            return httpx.Response(
                200,
                json={
                    "issuer": "http://casdoor.local",
                    "authorization_endpoint": "http://casdoor.local/login/oauth/authorize",
                    "token_endpoint": "http://casdoor.local/api/login/oauth/access_token",
                    "jwks_uri": "http://casdoor.local/.well-known/jwks",
                },
            )
        if request.url.path == "/.well-known/jwks":
            index = min(calls["jwks"], len(keys) - 1)
            calls["jwks"] += 1
            return httpx.Response(200, json={"keys": [keys[index].jwk]})
        if request.url.path == "/api/login/oauth/access_token":
            form = parse_qs(request.content.decode("utf-8"))
            assert form["grant_type"] == ["authorization_code"]
            assert form["client_id"] == ["team-api"]
            assert form["client_secret"] == ["client-secret"]
            return httpx.Response(
                200,
                json={
                    "access_token": "access-token",
                    "id_token": _id_token(keys[-1]),
                    "token_type": "Bearer",
                    "expires_in": 3600,
                },
            )
        return httpx.Response(404)

    return httpx.MockTransport(handler)


def test_authorization_url_uses_code_flow_state_nonce_and_pkce():
    from team_cloud.auth.oidc import CasdoorOIDCClient

    client = CasdoorOIDCClient(_config(), http_client=httpx.Client(transport=_transport([_signing_key("k1")])))

    authorization_url = client.authorization_url(
        redirect_uri="http://localhost:8780/auth/oidc/callback",
        state="state-123",
        nonce="nonce-123",
        code_challenge="challenge-123",
    )

    parsed = urlparse(authorization_url)
    params = parse_qs(parsed.query)
    assert parsed.geturl().startswith("http://casdoor.local/login/oauth/authorize")
    assert params["response_type"] == ["code"]
    assert params["client_id"] == ["team-api"]
    assert params["state"] == ["state-123"]
    assert params["nonce"] == ["nonce-123"]
    assert params["code_challenge"] == ["challenge-123"]
    assert params["code_challenge_method"] == ["S256"]


def test_exchange_code_posts_to_token_endpoint():
    from team_cloud.auth.oidc import CasdoorOIDCClient

    client = CasdoorOIDCClient(_config(), http_client=httpx.Client(transport=_transport([_signing_key("k1")])))

    token_set = client.exchange_code(
        code="code-123",
        redirect_uri="http://localhost:8780/auth/oidc/callback",
        code_verifier="verifier-123",
    )

    assert token_set.access_token == "access-token"
    assert token_set.token_type == "Bearer"
    assert "client-secret" not in repr(token_set)


def test_verify_id_token_checks_claims_and_signature():
    from team_cloud.auth.oidc import CasdoorOIDCClient

    key = _signing_key("k1")
    client = CasdoorOIDCClient(_config(), http_client=httpx.Client(transport=_transport([key])))

    claims = client.verify_id_token(_id_token(key), nonce="nonce-123")

    assert claims["sub"] == "casdoor-user-1"
    assert claims["email"] == "admin@example.com"


def test_verify_id_token_rejects_wrong_audience():
    from team_cloud.auth.oidc import CasdoorOIDCClient, OIDCVerificationError

    key = _signing_key("k1")
    client = CasdoorOIDCClient(_config(), http_client=httpx.Client(transport=_transport([key])))

    with pytest.raises(OIDCVerificationError):
        client.verify_id_token(_id_token(key, audience="other-client"), nonce="nonce-123")


def test_jwks_cache_refreshes_for_key_rotation():
    from team_cloud.auth.oidc import CasdoorOIDCClient

    old_key = _signing_key("old")
    new_key = _signing_key("new")
    client = CasdoorOIDCClient(
        _config(),
        http_client=httpx.Client(transport=_transport([old_key, new_key])),
    )

    assert client.verify_id_token(_id_token(old_key), nonce="nonce-123")["sub"]
    assert client.verify_id_token(_id_token(new_key), nonce="nonce-123")["sub"]


def test_api_exposes_oidc_authorize_and_callback_routes():
    from team_cloud.api import create_app

    class FakeOIDCClient:
        def authorization_url(self, **kwargs):
            assert kwargs["state"]
            assert kwargs["nonce"]
            return "http://casdoor.local/login/oauth/authorize?state=" + kwargs["state"]

        def exchange_code(self, **kwargs):
            assert kwargs["code"] == "code-123"
            return type("TokenSet", (), {"id_token": "id-token"})()

        def verify_id_token(self, token, **kwargs):
            assert token == "id-token"
            return {"sub": "casdoor-user-1", "email": "admin@example.com", "name": "Admin"}

    client = TestClient(create_app(_config(), oidc_client=FakeOIDCClient()))

    authorize = client.get(
        "/auth/oidc/authorize",
        params={"redirect_uri": "http://localhost:8780/auth/oidc/callback"},
    )
    assert authorize.status_code == 200
    assert authorize.json()["authorization_url"].startswith("http://casdoor.local")

    callback = client.get(
        "/auth/oidc/callback",
        params={
            "code": "code-123",
            "state": authorize.json()["state"],
            "redirect_uri": "http://localhost:8780/auth/oidc/callback",
            "nonce": authorize.json()["nonce"],
        },
    )
    assert callback.status_code == 200
    assert callback.json()["subject"] == "casdoor-user-1"
    assert "id-token" not in json.dumps(callback.json())
