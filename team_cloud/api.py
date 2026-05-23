"""FastAPI application factory for the Team Cloud service."""

from __future__ import annotations

import secrets
import time
from typing import Any

from . import __version__
from .auth.middleware import install_jwt_middleware
from .auth.oidc import CasdoorOIDCClient
from .config import TeamCloudConfig, load_config
from .context import RequestContext
from .migrations import MigrationRunner
from .observability import InMemoryObservability


def _require_fastapi():
    try:
        from fastapi import FastAPI, Request
    except ImportError as exc:  # pragma: no cover - exercised in lean installs
        raise RuntimeError(
            "Team Cloud API requires the web extra: hermes-agent[web]"
        ) from exc
    return FastAPI, Request


def create_app(
    config: TeamCloudConfig | None = None,
    *,
    oidc_client: Any | None = None,
    enable_jwt_middleware: bool = False,
    member_status_resolver: Any | None = None,
    organization_service: Any | None = None,
    audit_log: Any | None = None,
    authz_client: Any | None = None,
    relationship_outbox_repository: Any | None = None,
    enable_authz_middleware: bool = False,
    authz_subject_resolver: Any | None = None,
    authz_outbox_pending: Any | None = None,
    memory_service: Any | None = None,
    memory_observation_repository: Any | None = None,
    memory_prefetch_pipeline: Any | None = None,
    memory_review_service: Any | None = None,
    backup_policy_service: Any | None = None,
    external_identity_resolver: Any | None = None,
    chat_run_service: Any | None = None,
    cloud_session_repository: Any | None = None,
    runtime_event_bridge: Any | None = None,
    object_manifest_service: Any | None = None,
    usage_quota_service: Any | None = None,
    notification_service: Any | None = None,
):
    FastAPI, Request = _require_fastapi()
    globals()["_FastAPIRequest"] = Request
    resolved_config = config or load_config()
    app = FastAPI(title="Hermes Team Cloud", version=__version__)
    app.state.config = resolved_config
    app.state.oidc_client = oidc_client or CasdoorOIDCClient(resolved_config)
    app.state.authz_client = authz_client
    app.state.relationship_outbox_repository = relationship_outbox_repository
    app.state.memory_service = memory_service
    app.state.memory_observation_repository = memory_observation_repository
    app.state.memory_prefetch_pipeline = memory_prefetch_pipeline
    app.state.memory_review_service = memory_review_service
    if backup_policy_service is None:
        from team_cloud.backup.policy import BackupPolicyService

        backup_policy_service = BackupPolicyService()
    app.state.backup_policy_service = backup_policy_service
    app.state.external_identity_resolver = external_identity_resolver
    if cloud_session_repository is None:
        from team_cloud.cloud_sessions import InMemoryCloudSessionRepository

        cloud_session_repository = InMemoryCloudSessionRepository()
    app.state.cloud_session_repository = cloud_session_repository
    if chat_run_service is None:
        from team_cloud.chat import InMemoryChatRunService

        chat_run_service = InMemoryChatRunService(
            cloud_session_repository=cloud_session_repository,
        )
    app.state.chat_run_service = chat_run_service
    if runtime_event_bridge is None:
        from team_cloud.runtime_events import RuntimeEventBridge

        runtime_event_bridge = RuntimeEventBridge(
            cloud_session_repository=cloud_session_repository,
            chat_run_service=chat_run_service,
        )
    app.state.runtime_event_bridge = runtime_event_bridge
    if usage_quota_service is None:
        from team_cloud.usage import UsageQuotaService

        usage_quota_service = UsageQuotaService(
            cloud_session_repository=cloud_session_repository,
            chat_run_service=chat_run_service,
            object_manifest_service=object_manifest_service,
            audit_log=audit_log,
        )
    app.state.usage_quota_service = usage_quota_service
    if notification_service is None:
        from team_cloud.notifications import InMemoryNotificationService

        notification_service = InMemoryNotificationService()
    app.state.notification_service = notification_service
    app.state.observability = InMemoryObservability()
    if enable_jwt_middleware:
        install_jwt_middleware(
            app,
            oidc_client=app.state.oidc_client,
            member_status_resolver=member_status_resolver,
        )
    if enable_authz_middleware:
        from team_cloud.authz.middleware import (
            RoutePermissionRule,
            install_authz_middleware,
        )

        install_authz_middleware(
            app,
            authz_client=authz_client,
            route_permissions=[
                RoutePermissionRule(
                    method="POST",
                    path_template="/api/organizations/{org_id}/teams",
                    resource_type="organization",
                    resource_id_param="org_id",
                    permission="manage",
                ),
                RoutePermissionRule(
                    method="GET",
                    path_template="/api/organizations/{org_id}/teams",
                    resource_type="organization",
                    resource_id_param="org_id",
                    permission="view",
                ),
                RoutePermissionRule(
                    method="GET",
                    path_template="/api/organizations/{org_id}/members",
                    resource_type="organization",
                    resource_id_param="org_id",
                    permission="manage_members",
                ),
                RoutePermissionRule(
                    method="POST",
                    path_template="/api/organizations/{org_id}/members/invite",
                    resource_type="organization",
                    resource_id_param="org_id",
                    permission="manage_members",
                ),
                RoutePermissionRule(
                    method="PATCH",
                    path_template="/api/organizations/{org_id}/members/{member_id}/disable",
                    resource_type="organization",
                    resource_id_param="org_id",
                    permission="manage_members",
                ),
            ],
            subject_resolver=authz_subject_resolver,
            outbox_pending=authz_outbox_pending,
        )

    @app.middleware("http")
    async def request_context_middleware(request: Request, call_next):
        context = RequestContext.from_headers(request.headers)
        request.state.context = context
        response = await call_next(request)
        response.headers.setdefault("x-request-id", context.request_id)
        return response

    @app.middleware("http")
    async def observability_middleware(request: Request, call_next):
        started_at = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - started_at) * 1000
        context = getattr(request.state, "context", None)
        app.state.observability.record_request(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
            request_id=getattr(context, "request_id", None),
            run_id=getattr(request.state, "run_id", None),
            audit_event_id=getattr(request.state, "audit_event_id", None),
            trace_id=getattr(context, "trace_id", None),
            correlation_id=getattr(request.state, "correlation_id", None),
        )
        return response

    if audit_log is not None:

        @app.middleware("http")
        async def audit_middleware(request: Request, call_next):
            response = await call_next(request)
            if not request.url.path.startswith("/api/audit/"):
                context = getattr(request.state, "context", None)
                audit_event = audit_log.record(
                    action="http.request",
                    resource_type="api_route",
                    decision="allowed" if response.status_code < 400 else "error",
                    request_id=getattr(context, "request_id", None),
                    run_id=getattr(request.state, "run_id", None),
                    trace_id=getattr(context, "trace_id", None),
                    correlation_id=getattr(request.state, "correlation_id", None),
                    metadata={
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": response.status_code,
                    },
                )
                request.state.audit_event_id = audit_event["id"]
                request.state.correlation_id = audit_event["correlation_id"]
            return response

    @app.get("/healthz")
    def healthz() -> dict[str, Any]:
        return {
            "service": "team-cloud-api",
            "status": "ok",
            "version": __version__,
        }

    @app.get("/readyz")
    def readyz() -> dict[str, Any]:
        migrations = MigrationRunner.default().plan()
        checks = {
            "config": isinstance(app.state.config, TeamCloudConfig),
            "migrations": bool(migrations),
        }
        status = "ready" if all(checks.values()) else "not_ready"
        return {
            "service": "team-cloud-api",
            "status": status,
            "checks": checks,
        }

    @app.get("/metrics")
    def metrics():
        from fastapi import Response

        return Response(
            app.state.observability.render_prometheus(),
            media_type="text/plain; version=0.0.4",
        )

    @app.get("/auth/oidc/authorize")
    def oidc_authorize(
        redirect_uri: str,
        code_challenge: str | None = None,
    ) -> dict[str, str]:
        state = secrets.token_urlsafe(24)
        nonce = secrets.token_urlsafe(24)
        authorization_url = app.state.oidc_client.authorization_url(
            redirect_uri=redirect_uri,
            state=state,
            nonce=nonce,
            code_challenge=code_challenge,
        )
        return {
            "authorization_url": authorization_url,
            "state": state,
            "nonce": nonce,
        }

    @app.get("/auth/oidc/callback")
    def oidc_callback(
        code: str,
        state: str,
        redirect_uri: str,
        nonce: str | None = None,
        code_verifier: str | None = None,
    ) -> dict[str, str | None]:
        token_set = app.state.oidc_client.exchange_code(
            code=code,
            redirect_uri=redirect_uri,
            code_verifier=code_verifier,
        )
        claims = app.state.oidc_client.verify_id_token(
            token_set.id_token,
            nonce=nonce,
        )
        return {
            "subject": str(claims["sub"]),
            "email": claims.get("email"),
            "name": claims.get("name"),
            "state": state,
        }

    @app.get("/api/whoami")
    def whoami(request: _FastAPIRequest) -> dict[str, str | None]:
        from fastapi import HTTPException

        principal = getattr(request.state, "principal", None)
        if principal is None:
            raise HTTPException(status_code=401, detail="missing_principal")
        return {
            "subject": principal.subject,
            "email": principal.email,
            "name": principal.name,
            "member_status": principal.member_status,
        }

    @app.get("/api/authz/explain")
    def authz_explain(
        subject_type: str,
        subject_id: str,
        resource_type: str,
        resource_id: str,
        action: str | None = None,
        permission: str | None = None,
    ) -> dict[str, Any]:
        from fastapi import HTTPException

        from team_cloud.authz.explain import explain_permission

        try:
            return explain_permission(
                authz_client=app.state.authz_client,
                subject_type=subject_type,
                subject_id=subject_id,
                resource_type=resource_type,
                resource_id=resource_id,
                action=action,
                permission=permission,
                relationship_outbox_repository=app.state.relationship_outbox_repository,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    if organization_service is not None:
        from fastapi import HTTPException
        from starlette.status import HTTP_201_CREATED

        from team_cloud.admin.organizations import MemberNotFound, OrganizationNotFound

        @app.post("/api/organizations", status_code=HTTP_201_CREATED)
        def create_organization(payload: dict[str, str]) -> dict[str, Any]:
            return organization_service.create_organization(
                slug=payload["slug"],
                name=payload["name"],
            )

        @app.get("/api/organizations")
        def list_organizations() -> dict[str, list[dict[str, Any]]]:
            return {"items": organization_service.list_organizations()}

        @app.post("/api/organizations/{org_id}/teams", status_code=HTTP_201_CREATED)
        def create_team(org_id: str, payload: dict[str, str]) -> dict[str, Any]:
            try:
                return organization_service.create_team(
                    org_id=org_id,
                    slug=payload["slug"],
                    name=payload["name"],
                )
            except OrganizationNotFound as exc:
                raise HTTPException(
                    status_code=404,
                    detail="organization_not_found",
                ) from exc

        @app.get("/api/organizations/{org_id}/teams")
        def list_teams(org_id: str) -> dict[str, list[dict[str, Any]]]:
            try:
                return {"items": organization_service.list_teams(org_id=org_id)}
            except OrganizationNotFound as exc:
                raise HTTPException(
                    status_code=404,
                    detail="organization_not_found",
                ) from exc

        @app.get("/api/organizations/{org_id}/members")
        def list_members(org_id: str) -> dict[str, list[dict[str, Any]]]:
            try:
                return {"items": organization_service.list_members(org_id=org_id)}
            except OrganizationNotFound as exc:
                raise HTTPException(
                    status_code=404,
                    detail="organization_not_found",
                ) from exc

        @app.post(
            "/api/organizations/{org_id}/members/invite",
            status_code=HTTP_201_CREATED,
        )
        def invite_member(org_id: str, payload: dict[str, str]) -> dict[str, Any]:
            try:
                return organization_service.invite_member(
                    org_id=org_id,
                    email=payload["email"],
                    display_name=payload.get("display_name", ""),
                    user_id=payload["user_id"],
                    role=payload.get("role", "member"),
                )
            except OrganizationNotFound as exc:
                raise HTTPException(
                    status_code=404,
                    detail="organization_not_found",
                ) from exc

        @app.patch("/api/organizations/{org_id}/members/{member_id}/disable")
        def disable_member(org_id: str, member_id: str) -> dict[str, Any]:
            try:
                return organization_service.disable_member(
                    org_id=org_id,
                    member_id=member_id,
                )
            except MemberNotFound as exc:
                raise HTTPException(status_code=404, detail="member_not_found") from exc

    if external_identity_resolver is not None:
        from fastapi import HTTPException

        @app.post("/v1/external-identities/resolve")
        def resolve_external_identity(payload: dict[str, Any]) -> dict[str, Any]:
            try:
                return external_identity_resolver.resolve(payload)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc

    if chat_run_service is not None:
        from fastapi import HTTPException
        from starlette.status import HTTP_201_CREATED

        @app.post("/api/chat/runs", status_code=HTTP_201_CREATED)
        def create_chat_run(
            payload: dict[str, Any],
            request: _FastAPIRequest,
        ) -> dict[str, Any]:
            from fastapi.responses import JSONResponse

            try:
                _check_chat_run_permission(authz_client=authz_client, payload=payload)
                quota_decision = app.state.usage_quota_service.check_next_run(
                    payload["org_id"]
                )
                if not quota_decision["allowed"]:
                    return JSONResponse(
                        status_code=429,
                        content={
                            "detail": "quota_exceeded",
                            "violations": quota_decision["violations"],
                        },
                    )
                context = getattr(request.state, "context", None)
                run = app.state.chat_run_service.create_run(
                    org_id=payload["org_id"],
                    team_id=payload["team_id"],
                    project_id=payload["project_id"],
                    member_id=payload["member_id"],
                    message=payload["message"],
                    cloud_session_id=payload.get("cloud_session_id") or payload.get("session_id"),
                    request_id=getattr(context, "request_id", None),
                    trace_id=getattr(context, "trace_id", None),
                )
                request.state.run_id = run["id"]
                request.state.correlation_id = run.get("correlation_id")
                return run
            except KeyError as exc:
                raise HTTPException(
                    status_code=400,
                    detail=f"{exc.args[0]}_required",
                ) from exc
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc

        @app.get("/api/chat/runs/{run_id}/events")
        def list_chat_run_events(run_id: str) -> dict[str, list[dict[str, Any]]]:
            from team_cloud.chat import ChatRunNotFound

            try:
                return {"items": app.state.chat_run_service.list_events(run_id)}
            except ChatRunNotFound as exc:
                raise HTTPException(status_code=404, detail="chat_run_not_found") from exc

    if cloud_session_repository is not None:
        from fastapi import HTTPException
        from starlette.status import HTTP_201_CREATED

        @app.get("/api/cloud/sessions")
        def list_cloud_sessions(
            org_id: str | None = None,
            project_id: str | None = None,
            member_id: str | None = None,
            q: str | None = None,
        ) -> dict[str, list[dict[str, Any]]]:
            return {
                "items": app.state.cloud_session_repository.list_sessions(
                    org_id=org_id,
                    project_id=project_id,
                    member_id=member_id,
                    q=q,
                )
            }

        @app.get("/api/cloud/sessions/{session_id}")
        def get_cloud_session(session_id: str) -> dict[str, Any]:
            from team_cloud.cloud_sessions import CloudSessionNotFound

            try:
                return app.state.cloud_session_repository.get_session(session_id)
            except CloudSessionNotFound as exc:
                raise HTTPException(status_code=404, detail="cloud_session_not_found") from exc

        @app.post(
            "/api/cloud/sessions/{session_id}/tool-calls",
            status_code=HTTP_201_CREATED,
        )
        def create_cloud_tool_call(
            session_id: str,
            payload: dict[str, Any],
        ) -> dict[str, Any]:
            from team_cloud.cloud_sessions import CloudSessionNotFound

            try:
                return app.state.cloud_session_repository.append_tool_call(
                    session_id=session_id,
                    org_id=payload["org_id"],
                    actor_member_id=payload.get("actor_member_id"),
                    tool_name=payload["tool_name"],
                    risk_level=payload["risk_level"],
                    decision=payload["decision"],
                    input_redacted=payload.get("input_redacted", {}),
                    output_redacted=payload.get("output_redacted"),
                    error=payload.get("error"),
                    run_id=payload.get("run_id"),
                )
            except CloudSessionNotFound as exc:
                raise HTTPException(status_code=404, detail="cloud_session_not_found") from exc
            except KeyError as exc:
                raise HTTPException(
                    status_code=400,
                    detail=f"{exc.args[0]}_required",
                ) from exc
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc

    if runtime_event_bridge is not None:
        from fastapi import HTTPException
        from starlette.status import HTTP_202_ACCEPTED

        @app.post("/api/runtime/events", status_code=HTTP_202_ACCEPTED)
        def ingest_runtime_event(
            payload: dict[str, Any],
            request: _FastAPIRequest,
        ) -> dict[str, Any]:
            from team_cloud.chat import ChatRunNotFound
            from team_cloud.cloud_sessions import CloudSessionNotFound

            try:
                context = getattr(request.state, "context", None)
                enriched_payload = dict(payload)
                enriched_payload.setdefault(
                    "request_id",
                    getattr(context, "request_id", None),
                )
                enriched_payload.setdefault("trace_id", getattr(context, "trace_id", None))
                result = app.state.runtime_event_bridge.ingest(enriched_payload)
                request.state.run_id = result["event"].get("run_id")
                request.state.correlation_id = result["event"].get("correlation_id")
                return result
            except CloudSessionNotFound as exc:
                raise HTTPException(status_code=404, detail="cloud_session_not_found") from exc
            except ChatRunNotFound as exc:
                raise HTTPException(status_code=404, detail="chat_run_not_found") from exc
            except KeyError as exc:
                raise HTTPException(
                    status_code=400,
                    detail=f"{exc.args[0]}_required",
                ) from exc
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc

    if memory_service is not None:
        from fastapi import HTTPException
        from starlette.status import HTTP_201_CREATED

        from team_cloud.memory.service import MemoryNotFound

        @app.post("/v1/memory", status_code=HTTP_201_CREATED)
        def create_memory(payload: dict[str, Any]) -> dict[str, Any]:
            try:
                return memory_service.create_memory(payload)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc

        @app.get("/v1/memory")
        def list_memory(
            org_id: str,
            scope: str | None = None,
            status: str | None = None,
            memory_type: str | None = None,
            sensitivity: str | None = None,
        ) -> dict[str, list[dict[str, Any]]]:
            return {
                "items": memory_service.list_memory(
                    org_id=org_id,
                    scope=scope,
                    status=status,
                    memory_type=memory_type,
                    sensitivity=sensitivity,
                )
            }

        @app.patch("/v1/memory/{memory_id}")
        def update_memory(memory_id: str, payload: dict[str, Any]) -> dict[str, Any]:
            try:
                return memory_service.update_memory(memory_id, payload)
            except MemoryNotFound as exc:
                raise HTTPException(status_code=404, detail="memory_not_found") from exc

        @app.post("/v1/memory/{memory_id}/archive")
        def archive_memory(memory_id: str, payload: dict[str, Any]) -> dict[str, Any]:
            try:
                return memory_service.archive_memory(
                    memory_id,
                    actor_member_id=payload.get("actor_member_id"),
                )
            except MemoryNotFound as exc:
                raise HTTPException(status_code=404, detail="memory_not_found") from exc

        @app.delete("/v1/memory/{memory_id}")
        def delete_memory(
            memory_id: str,
            actor_member_id: str | None = None,
        ) -> dict[str, Any]:
            try:
                return memory_service.delete_memory(
                    memory_id,
                    actor_member_id=actor_member_id,
                )
            except MemoryNotFound as exc:
                raise HTTPException(status_code=404, detail="memory_not_found") from exc

        @app.post("/v1/memory/{memory_id}/restore")
        def restore_memory(memory_id: str, payload: dict[str, Any]) -> dict[str, Any]:
            try:
                return memory_service.restore_memory(
                    memory_id,
                    actor_member_id=payload.get("actor_member_id"),
                )
            except MemoryNotFound as exc:
                raise HTTPException(status_code=404, detail="memory_not_found") from exc

    if memory_observation_repository is not None:
        from fastapi import HTTPException
        from starlette.status import HTTP_201_CREATED

        @app.post("/v1/memory/observations", status_code=HTTP_201_CREATED)
        def create_memory_observation(payload: dict[str, Any]) -> dict[str, Any]:
            try:
                normalized = _normalize_memory_observation_payload(payload)
                observation = memory_observation_repository.create_observation(
                    org_id=normalized["org_id"],
                    session_id=normalized.get("session_id"),
                    member_id=normalized.get("member_id"),
                    team_id=normalized.get("team_id"),
                    project_id=normalized.get("project_id"),
                    observation=normalized["observation"],
                )
            except (KeyError, ValueError) as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            return _memory_observation_response(observation)

    if memory_prefetch_pipeline is not None:

        @app.post("/v1/memory/prefetch")
        def prefetch_memory(payload: dict[str, Any]) -> dict[str, object]:
            return memory_prefetch_pipeline.prefetch(
                query=payload["query"],
                org_id=payload["org_id"],
                member_id=payload["member_id"],
                team_id=payload["team_id"],
                project_id=payload.get("project_id"),
                limit=int(payload.get("limit", 8)),
                include_personal=bool(payload.get("include_personal", True)),
            )

    if memory_review_service is not None:
        from fastapi import HTTPException

        from team_cloud.memory.review import ReviewItemNotFound, ReviewItemStateError

        @app.get("/v1/memory/review")
        def list_memory_review(
            org_id: str,
            status: str = "pending",
            review_kind: str | None = None,
            limit: int = 100,
        ) -> dict[str, list[dict[str, Any]]]:
            return {
                "items": memory_review_service.list_review_items(
                    org_id=org_id,
                    status=status,
                    review_kind=review_kind,
                    limit=limit,
                )
            }

        @app.post("/v1/memory/review/{review_id}/approve")
        def approve_memory_review(review_id: str, payload: dict[str, Any]) -> dict[str, Any]:
            try:
                edits = {
                    field_name: payload[field_name]
                    for field_name in ("content", "memory_type", "sensitivity")
                    if field_name in payload
                }
                return memory_review_service.approve_review_item(
                    review_id,
                    actor_member_id=payload["actor_member_id"],
                    edits=edits,
                )
            except ReviewItemNotFound as exc:
                raise HTTPException(status_code=404, detail="review_item_not_found") from exc
            except ReviewItemStateError as exc:
                raise HTTPException(status_code=409, detail=str(exc)) from exc

        @app.post("/v1/memory/review/{review_id}/reject")
        def reject_memory_review(review_id: str, payload: dict[str, Any]) -> dict[str, Any]:
            try:
                return memory_review_service.reject_review_item(
                    review_id,
                    actor_member_id=payload["actor_member_id"],
                    reason=payload.get("reason"),
                )
            except ReviewItemNotFound as exc:
                raise HTTPException(status_code=404, detail="review_item_not_found") from exc
            except ReviewItemStateError as exc:
                raise HTTPException(status_code=409, detail=str(exc)) from exc

    if backup_policy_service is not None:
        from fastapi import HTTPException

        @app.get("/v1/me/memory-backup-policy")
        def get_memory_backup_policy(org_id: str, member_id: str) -> dict[str, Any]:
            try:
                return app.state.backup_policy_service.get_policy(
                    org_id=org_id,
                    member_id=member_id,
                )
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc

        @app.put("/v1/me/memory-backup-policy")
        def update_memory_backup_policy(payload: dict[str, Any]) -> dict[str, Any]:
            try:
                return app.state.backup_policy_service.upsert_policy(
                    org_id=payload["org_id"],
                    member_id=payload["member_id"],
                    cadence=payload.get("cadence"),
                    enabled=payload.get("enabled"),
                    retention_count=payload.get("retention_count"),
                    include_archived=payload.get("include_archived"),
                    include_deleted=payload.get("include_deleted"),
                    include_embeddings=payload.get("include_embeddings"),
                    encryption_mode=payload.get("encryption_mode"),
                    notification_channels=payload.get("notification_channels"),
                    next_run_at=payload.get("next_run_at"),
                )
            except KeyError as exc:
                raise HTTPException(
                    status_code=400,
                    detail=f"{exc.args[0]}_required",
                ) from exc
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc

    if usage_quota_service is not None:
        from fastapi import HTTPException

        from team_cloud.usage import QUOTA_METRICS

        @app.get("/api/usage/orgs/{org_id}/summary")
        def get_org_usage_summary(org_id: str) -> dict[str, Any]:
            return app.state.usage_quota_service.org_summary(org_id)

        @app.get("/api/usage/orgs/{org_id}/quotas")
        def get_org_usage_quotas(org_id: str) -> dict[str, Any]:
            return {
                "org_id": org_id,
                "quotas": app.state.usage_quota_service.get_org_quotas(org_id),
            }

        @app.put("/api/usage/orgs/{org_id}/quotas")
        def update_org_usage_quotas(
            org_id: str,
            payload: dict[str, Any],
        ) -> dict[str, Any]:
            try:
                updates = {
                    metric: payload[metric]
                    for metric in QUOTA_METRICS
                    if metric in payload
                }
                quotas = app.state.usage_quota_service.set_org_quotas(
                    org_id,
                    actor_member_id=payload.get("actor_member_id"),
                    **updates,
                )
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            return {"org_id": org_id, "quotas": quotas}

    if notification_service is not None:
        from fastapi import HTTPException

        from team_cloud.notifications import NotificationNotFound

        @app.get("/api/notifications")
        def list_notifications(
            org_id: str,
            recipient_member_id: str | None = None,
            status: str | None = None,
            notification_type: str | None = None,
            limit: int = 100,
        ) -> dict[str, list[dict[str, Any]]]:
            return {
                "items": app.state.notification_service.list_notifications(
                    org_id=org_id,
                    recipient_member_id=recipient_member_id,
                    status=status,
                    notification_type=notification_type,
                    limit=limit,
                )
            }

        @app.post("/api/notifications/{notification_id}/ack")
        def acknowledge_notification(
            notification_id: str,
            payload: dict[str, Any],
        ) -> dict[str, Any]:
            try:
                return app.state.notification_service.acknowledge(
                    notification_id,
                    actor_member_id=payload["actor_member_id"],
                )
            except NotificationNotFound as exc:
                raise HTTPException(
                    status_code=404,
                    detail="notification_not_found",
                ) from exc
            except KeyError as exc:
                raise HTTPException(
                    status_code=400,
                    detail=f"{exc.args[0]}_required",
                ) from exc

    if audit_log is not None:

        @app.get("/api/audit/events")
        def list_audit_events(
            org_id: str | None = None,
            action: str | None = None,
            actor_member_id: str | None = None,
            actor_type: str | None = None,
            resource_type: str | None = None,
            resource_id: str | None = None,
            decision: str | None = None,
            created_after: str | None = None,
            created_before: str | None = None,
            limit: int = 100,
        ) -> dict[str, list[dict[str, Any]]]:
            return {
                "items": audit_log.query(
                    org_id=org_id,
                    action=action,
                    actor_member_id=actor_member_id,
                    actor_type=actor_type,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    decision=decision,
                    created_after=created_after,
                    created_before=created_before,
                    limit=limit,
                )
            }

        @app.get("/api/audit/sensitive-reads")
        def list_sensitive_audit_reads(
            org_id: str | None = None,
            actor_member_id: str | None = None,
            limit: int = 100,
        ) -> dict[str, list[dict[str, Any]]]:
            return {
                "items": audit_log.sensitive_reads(
                    org_id=org_id,
                    actor_member_id=actor_member_id,
                    limit=limit,
                )
            }

        @app.get("/api/audit/high-risk-tools")
        def list_high_risk_tool_audit_events(
            org_id: str | None = None,
            actor_member_id: str | None = None,
            limit: int = 100,
        ) -> dict[str, list[dict[str, Any]]]:
            return {
                "items": audit_log.high_risk_tools(
                    org_id=org_id,
                    actor_member_id=actor_member_id,
                    limit=limit,
                )
            }

        @app.get("/api/audit/export")
        def export_audit_events(
            org_id: str | None = None,
            action: str | None = None,
            actor_member_id: str | None = None,
            actor_type: str | None = None,
            resource_type: str | None = None,
            resource_id: str | None = None,
            decision: str | None = None,
            created_after: str | None = None,
            created_before: str | None = None,
            limit: int = 100,
        ):
            from fastapi import Response

            return Response(
                audit_log.export_jsonl(
                    org_id=org_id,
                    action=action,
                    actor_member_id=actor_member_id,
                    actor_type=actor_type,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    decision=decision,
                    created_after=created_after,
                    created_before=created_before,
                    limit=limit,
                ),
                media_type="application/x-ndjson",
                headers={"Content-Disposition": 'attachment; filename="audit-events.jsonl"'},
            )

    return app


def _check_chat_run_permission(
    *,
    authz_client: Any | None,
    payload: dict[str, Any],
) -> None:
    from fastapi import HTTPException

    from team_cloud.authz.spicedb import ResourceRef, SubjectRef

    if authz_client is None:
        raise HTTPException(status_code=403, detail="authz_client_not_configured")
    try:
        subject = SubjectRef("user", str(payload["member_id"]))
        resource = ResourceRef("project", str(payload["project_id"]))
        decision = authz_client.check(
            subject=subject,
            resource=resource,
            action="chat.run",
            consistency="fully_consistent_for_sensitive",
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"{exc.args[0]}_required",
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=403, detail="authorization_unavailable") from exc
    if decision.reason == "spicedb_error":
        raise HTTPException(status_code=403, detail="authorization_unavailable")
    if not decision.allowed:
        raise HTTPException(status_code=403, detail="permission_denied")


def _normalize_memory_observation_payload(payload: dict[str, Any]) -> dict[str, Any]:
    observation = payload["observation"]
    if not isinstance(observation, dict):
        raise ValueError("observation must be an object")
    normalized_observation = dict(observation)
    turn_metadata = normalized_observation.get("turn_metadata", {})
    if not isinstance(turn_metadata, dict):
        raise ValueError("turn_metadata must be an object")
    tool_summaries = normalized_observation.get("tool_summaries", [])
    if not isinstance(tool_summaries, list):
        raise ValueError("tool_summaries must be a list")
    context = {
        "org_id": payload["org_id"],
        "session_id": payload.get("session_id"),
        "member_id": payload.get("member_id"),
        "team_id": payload.get("team_id"),
        "project_id": payload.get("project_id"),
    }
    _assert_observation_context_matches(normalized_observation, context)
    normalized_observation["context"] = context
    normalized_observation["turn_metadata"] = dict(turn_metadata)
    normalized_observation["tool_summaries"] = list(tool_summaries)
    return {
        "org_id": context["org_id"],
        "session_id": context["session_id"],
        "member_id": context["member_id"],
        "team_id": context["team_id"],
        "project_id": context["project_id"],
        "observation": normalized_observation,
    }


def _assert_observation_context_matches(
    observation: dict[str, Any],
    context: dict[str, Any],
) -> None:
    supplied_context = observation.get("context") or {}
    if not isinstance(supplied_context, dict):
        raise ValueError("context must be an object")
    for field_name, expected in context.items():
        supplied = supplied_context.get(field_name)
        if supplied is not None and expected is not None and str(supplied) != str(expected):
            raise ValueError(f"observation_context_mismatch: {field_name}")


def _memory_observation_response(observation: Any) -> dict[str, Any]:
    return {
        "id": observation.id,
        "org_id": observation.org_id,
        "session_id": observation.session_id,
        "member_id": observation.member_id,
        "team_id": observation.team_id,
        "project_id": observation.project_id,
        "status": observation.status,
        "created_at": observation.created_at,
    }
