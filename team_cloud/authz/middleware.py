"""FastAPI authorization middleware for Team Cloud APIs."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Callable

from fastapi.responses import JSONResponse

from .spicedb import ResourceRef, SubjectRef


SubjectResolver = Callable[[Any], SubjectRef | None]
OutboxPendingResolver = Callable[[str, str], bool]
CacheKeyCallback = Callable[[str], None]


@dataclass(frozen=True)
class RoutePermissionRule:
    method: str
    path_template: str
    resource_type: str
    resource_id_param: str
    action: str | None = None
    permission: str | None = None
    consistency: str = "minimize_latency"

    def match(self, *, method: str, path: str) -> dict[str, str] | None:
        if method.upper() != self.method.upper():
            return None
        pattern = _template_pattern(self.path_template)
        match = re.match(pattern, path)
        if not match:
            return None
        return match.groupdict()


def install_authz_middleware(
    app,
    *,
    authz_client,
    route_permissions: list[RoutePermissionRule],
    subject_resolver: SubjectResolver | None = None,
    outbox_pending: OutboxPendingResolver | None = None,
    cache_key_callback: CacheKeyCallback | None = None,
) -> None:
    resolve_subject = subject_resolver or _default_subject_resolver

    @app.middleware("http")
    async def authz_middleware(request, call_next):
        rule, params = _match_rule(
            route_permissions,
            method=request.method,
            path=request.url.path,
        )
        if rule is None:
            return await call_next(request)

        subject = resolve_subject(request)
        if subject is None:
            return JSONResponse({"detail": "missing_authorization_subject"}, status_code=401)

        resource_id = params.get(rule.resource_id_param)
        if not resource_id:
            return JSONResponse({"detail": "missing_authorization_resource"}, status_code=403)
        resource = ResourceRef(rule.resource_type, resource_id)

        if outbox_pending and outbox_pending(resource.type, resource.id):
            return JSONResponse(
                {"detail": "authorization_pending_relationship_sync"},
                status_code=403,
            )

        try:
            decision = authz_client.check(
                subject=subject,
                resource=resource,
                action=rule.action,
                permission=rule.permission,
                consistency=rule.consistency,
            )
        except Exception:
            return JSONResponse({"detail": "authorization_unavailable"}, status_code=403)

        cache_key = permission_cache_key(subject, resource, decision.permission)
        request.state.authz_cache_key = cache_key
        request.state.authz_decision = decision
        if cache_key_callback:
            cache_key_callback(cache_key)

        if decision.reason == "spicedb_error":
            return JSONResponse({"detail": "authorization_unavailable"}, status_code=403)
        if not decision.allowed:
            return JSONResponse({"detail": "permission_denied"}, status_code=403)
        return await call_next(request)


def permission_cache_key(
    subject: SubjectRef,
    resource: ResourceRef,
    permission: str,
) -> str:
    return f"{subject.as_spicedb()}|{resource.as_spicedb()}|{permission}"


def _match_rule(
    rules: list[RoutePermissionRule],
    *,
    method: str,
    path: str,
) -> tuple[RoutePermissionRule | None, dict[str, str]]:
    for rule in rules:
        params = rule.match(method=method, path=path)
        if params is not None:
            return rule, params
    return None, {}


def _default_subject_resolver(request) -> SubjectRef | None:
    token_principal = getattr(request.state, "token_principal", None)
    if token_principal is not None:
        if getattr(token_principal, "actor_type", None) == "service_account":
            service_account_id = getattr(token_principal, "service_account_id", None)
            return (
                SubjectRef("service_account", str(service_account_id))
                if service_account_id
                else None
            )
        member_id = getattr(token_principal, "member_id", None)
        return SubjectRef("user", str(member_id)) if member_id else None

    principal = getattr(request.state, "principal", None)
    if principal is None:
        return None
    subject = getattr(principal, "subject", None)
    return SubjectRef("user", str(subject)) if subject else None


def _template_pattern(path_template: str) -> str:
    escaped = re.escape(path_template)
    pattern = re.sub(r"\\\{([a-zA-Z_][a-zA-Z0-9_]*)\\\}", r"(?P<\1>[^/]+)", escaped)
    return f"^{pattern}$"
