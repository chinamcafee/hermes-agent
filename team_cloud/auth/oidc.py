"""Casdoor OIDC client primitives."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import httpx
import jwt
from jwt import PyJWTError
from jwt.algorithms import RSAAlgorithm

from team_cloud.config import TeamCloudConfig


class OIDCVerificationError(RuntimeError):
    """Raised when an OIDC token fails Team Cloud validation."""


@dataclass(frozen=True)
class OIDCDiscovery:
    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    jwks_uri: str


@dataclass(frozen=True)
class TokenSet:
    access_token: str
    id_token: str
    token_type: str
    expires_in: int | None = None


class CasdoorOIDCClient:
    def __init__(
        self,
        config: TeamCloudConfig,
        *,
        http_client: httpx.Client | None = None,
        algorithms: tuple[str, ...] = ("RS256",),
    ):
        self.config = config
        self.http_client = http_client or httpx.Client(timeout=10.0)
        self.algorithms = algorithms
        self._discovery: OIDCDiscovery | None = None
        self._jwks: dict[str, Any] | None = None

    def discovery(self) -> OIDCDiscovery:
        if self._discovery is None:
            discovery_url = (
                self.config.casdoor_base_url.rstrip("/")
                + "/.well-known/openid-configuration"
            )
            payload = self._get_json(discovery_url)
            self._discovery = OIDCDiscovery(
                issuer=str(payload["issuer"]),
                authorization_endpoint=str(payload["authorization_endpoint"]),
                token_endpoint=str(payload["token_endpoint"]),
                jwks_uri=str(payload["jwks_uri"]),
            )
        return self._discovery

    def authorization_url(
        self,
        *,
        redirect_uri: str,
        state: str,
        nonce: str,
        scope: str = "openid profile email",
        code_challenge: str | None = None,
        code_challenge_method: str = "S256",
    ) -> str:
        params = {
            "response_type": "code",
            "client_id": self.config.casdoor_client_id,
            "redirect_uri": redirect_uri,
            "scope": scope,
            "state": state,
            "nonce": nonce,
        }
        if code_challenge:
            params["code_challenge"] = code_challenge
            params["code_challenge_method"] = code_challenge_method
        return self.discovery().authorization_endpoint + "?" + urlencode(params)

    def exchange_code(
        self,
        *,
        code: str,
        redirect_uri: str,
        code_verifier: str | None = None,
    ) -> TokenSet:
        client_secret = (
            self.config.casdoor_client_secret.get_secret_value()
            if self.config.casdoor_client_secret is not None
            else ""
        )
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": self.config.casdoor_client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
        }
        if code_verifier:
            data["code_verifier"] = code_verifier
        response = self.http_client.post(self.discovery().token_endpoint, data=data)
        response.raise_for_status()
        payload = response.json()
        return TokenSet(
            access_token=str(payload["access_token"]),
            id_token=str(payload["id_token"]),
            token_type=str(payload.get("token_type", "Bearer")),
            expires_in=payload.get("expires_in"),
        )

    def verify_id_token(self, token: str, *, nonce: str | None = None) -> dict[str, Any]:
        try:
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")
            if not kid:
                raise OIDCVerificationError("id_token is missing kid header")
            key = self._signing_key(str(kid))
            claims = jwt.decode(
                token,
                key=key,
                algorithms=list(self.algorithms),
                audience=self.config.casdoor_client_id,
                issuer=self.discovery().issuer,
                options={"require": ["exp", "iat", "nbf", "iss", "aud", "sub"]},
            )
        except (PyJWTError, KeyError, httpx.HTTPError) as exc:
            raise OIDCVerificationError("id_token verification failed") from exc

        if nonce is not None and claims.get("nonce") != nonce:
            raise OIDCVerificationError("id_token nonce mismatch")
        return claims

    def _signing_key(self, kid: str):
        jwk = self._find_jwk(kid, refresh=False)
        if jwk is None:
            jwk = self._find_jwk(kid, refresh=True)
        if jwk is None:
            raise OIDCVerificationError(f"jwks does not contain kid: {kid}")
        return RSAAlgorithm.from_jwk(json.dumps(jwk))

    def _find_jwk(self, kid: str, *, refresh: bool) -> dict[str, Any] | None:
        if self._jwks is None or refresh:
            self._jwks = self._get_json(self.discovery().jwks_uri)
        for jwk in self._jwks.get("keys", []):
            if jwk.get("kid") == kid:
                return jwk
        return None

    def _get_json(self, url: str) -> dict[str, Any]:
        response = self.http_client.get(url)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise OIDCVerificationError(f"OIDC endpoint returned non-object JSON: {url}")
        return payload
