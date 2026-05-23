"""JWT authentication middleware for Team Cloud APIs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable

from fastapi.responses import JSONResponse

from .oidc import OIDCVerificationError

MemberStatusResolver = Callable[[dict[str, Any]], str | None]

PUBLIC_PATHS = frozenset(
    {
        "/healthz",
        "/readyz",
        "/auth/oidc/authorize",
        "/auth/oidc/callback",
        "/openapi.json",
        "/docs",
        "/redoc",
    }
)


@dataclass(frozen=True)
class TeamPrincipal:
    subject: str
    email: str | None
    name: str | None
    member_status: str
    claims: dict[str, Any]


def install_jwt_middleware(
    app,
    *,
    oidc_client,
    member_status_resolver: MemberStatusResolver | None = None,
    public_paths: Iterable[str] = PUBLIC_PATHS,
) -> None:
    public_path_set = frozenset(public_paths)

    @app.middleware("http")
    async def jwt_middleware(request, call_next):
        if request.url.path in public_path_set:
            return await call_next(request)

        authorization = request.headers.get("authorization", "")
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            return JSONResponse(
                {"detail": "missing_bearer_token"},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )

        try:
            claims = oidc_client.verify_id_token(token)
        except OIDCVerificationError:
            return JSONResponse(
                {"detail": "invalid_token"},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )

        member_status = (
            member_status_resolver(claims) if member_status_resolver else "active"
        )
        if member_status != "active":
            return JSONResponse({"detail": "member_not_active"}, status_code=403)

        request.state.principal = TeamPrincipal(
            subject=str(claims["sub"]),
            email=claims.get("email"),
            name=claims.get("name"),
            member_status="active",
            claims=claims,
        )
        return await call_next(request)
