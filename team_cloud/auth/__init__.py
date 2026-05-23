"""Authentication helpers for Team Cloud."""

from __future__ import annotations

from .middleware import TeamPrincipal, install_jwt_middleware
from .oidc import CasdoorOIDCClient, OIDCVerificationError, TokenSet
from .tokens import (
    InMemoryTokenRepository,
    IssuedToken,
    TokenAuthenticationError,
    TokenPrincipal,
    TokenService,
    hash_token,
    verify_token_hash,
)

__all__ = [
    "CasdoorOIDCClient",
    "InMemoryTokenRepository",
    "IssuedToken",
    "OIDCVerificationError",
    "TeamPrincipal",
    "TokenAuthenticationError",
    "TokenSet",
    "TokenPrincipal",
    "TokenService",
    "hash_token",
    "install_jwt_middleware",
    "verify_token_hash",
]
