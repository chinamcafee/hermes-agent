"""Gateway-side Team Cloud identity resolution."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Mapping, Protocol
from urllib.parse import quote

from gateway.session import SessionSource
from utils import is_truthy_value


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _session_component(value: str) -> str:
    return quote(str(value), safe="")


def build_team_session_key_prefix(team_context: Mapping[str, Any]) -> str | None:
    org_id = _clean(team_context.get("org_id"))
    team_id = _clean(team_context.get("team_id"))
    if not org_id or not team_id:
        return None
    return f"team:{_session_component(org_id)}:{_session_component(team_id)}"


def prefix_session_key_for_team(session_key: str, team_context: Mapping[str, Any] | None) -> str:
    if not session_key or not team_context:
        return session_key
    if session_key.startswith("team:"):
        return session_key
    prefix = build_team_session_key_prefix(team_context)
    if not prefix:
        return session_key
    return f"{prefix}:{session_key}"


@dataclass(frozen=True)
class GatewayTeamIdentityResolution:
    status: str
    team_context: dict[str, Any] | None = None
    binding_message: str | None = None
    session_key_prefix: str | None = None
    error: str | None = None

    @classmethod
    def disabled(cls) -> "GatewayTeamIdentityResolution":
        return cls(status="disabled")

    @classmethod
    def resolved(
        cls,
        *,
        team_context: Mapping[str, Any],
        session_key_prefix: str | None = None,
    ) -> "GatewayTeamIdentityResolution":
        context = dict(team_context)
        return cls(
            status="resolved",
            team_context=context,
            session_key_prefix=session_key_prefix or build_team_session_key_prefix(context),
        )

    @classmethod
    def unbound(cls, binding_message: str | None = None) -> "GatewayTeamIdentityResolution":
        return cls(
            status="unbound",
            binding_message=binding_message or default_binding_message(),
        )

    @classmethod
    def failed(cls, error: str) -> "GatewayTeamIdentityResolution":
        return cls(status="error", error=error)


class GatewayTeamIdentityHttpClient(Protocol):
    async def post_json(
        self,
        path: str,
        *,
        json: dict[str, Any],
        headers: dict[str, str],
    ) -> dict[str, Any]: ...


class HttpxGatewayTeamIdentityClient:
    def __init__(self, *, base_url: str, timeout_seconds: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    async def post_json(
        self,
        path: str,
        *,
        json: dict[str, Any],
        headers: dict[str, str],
    ) -> dict[str, Any]:
        import httpx

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                f"{self.base_url}{path}",
                json=json,
                headers={**headers, "Accept": "application/json"},
            )
            response.raise_for_status()
            data = response.json()
        if not isinstance(data, dict):
            raise ValueError("team identity resolver returned non-object JSON")
        return data


class GatewayTeamIdentityResolver:
    def __init__(
        self,
        *,
        team_cloud_url: str,
        service_token: str,
        http_client: GatewayTeamIdentityHttpClient | None = None,
    ) -> None:
        self.team_cloud_url = team_cloud_url.rstrip("/")
        self.service_token = service_token
        self.http_client = http_client or HttpxGatewayTeamIdentityClient(
            base_url=self.team_cloud_url,
        )

    async def resolve(
        self,
        source: SessionSource,
        *,
        shared_session: bool,
    ) -> GatewayTeamIdentityResolution:
        if not self.team_cloud_url or not self.service_token:
            return GatewayTeamIdentityResolution.failed("team_identity_not_configured")
        payload = source_payload(source, shared_session=shared_session)
        try:
            response = await self.http_client.post_json(
                "/v1/external-identities/resolve",
                json=payload,
                headers={"Authorization": f"Bearer {self.service_token}"},
            )
        except Exception as exc:
            return GatewayTeamIdentityResolution.failed(str(exc))
        return resolution_from_response(response, shared_session=shared_session)


class MisconfiguredGatewayTeamIdentityResolver:
    def __init__(self, message: str) -> None:
        self.message = message

    async def resolve(
        self,
        source: SessionSource,
        *,
        shared_session: bool,
    ) -> GatewayTeamIdentityResolution:
        return GatewayTeamIdentityResolution.failed(self.message)


def source_payload(source: SessionSource, *, shared_session: bool) -> dict[str, Any]:
    return {
        "platform": source.platform.value if source.platform else "",
        "external_user_id": source.user_id_alt or source.user_id,
        "external_team_id": source.guild_id,
        "external_channel_id": source.parent_chat_id or source.chat_id_alt or source.chat_id,
        "chat_type": source.chat_type,
        "shared_session": shared_session,
    }


def resolution_from_response(
    response: Mapping[str, Any],
    *,
    shared_session: bool,
) -> GatewayTeamIdentityResolution:
    status = _clean(response.get("status")).lower()
    if status == "resolved":
        raw_context = response.get("team_context")
        if not isinstance(raw_context, Mapping):
            return GatewayTeamIdentityResolution.failed("team_context_missing")
        context = dict(raw_context)
        if shared_session:
            context["personal_memory_enabled"] = False
        else:
            context.setdefault("personal_memory_enabled", True)
        return GatewayTeamIdentityResolution.resolved(
            team_context=context,
            session_key_prefix=_clean(response.get("session_key_prefix")) or None,
        )
    if status == "unbound":
        return GatewayTeamIdentityResolution.unbound(
            _clean(response.get("binding_message")) or None,
        )
    if status == "disabled":
        return GatewayTeamIdentityResolution.disabled()
    return GatewayTeamIdentityResolution.failed(status or "invalid_team_identity_response")


def default_binding_message() -> str:
    return (
        "This platform account is not bound to Hermes Team Cloud yet. "
        "Generate a gateway binding code in Team Cloud, then send the binding code here."
    )


def build_gateway_team_identity_resolver_from_config(
    config: Mapping[str, Any] | None = None,
    *,
    env: Mapping[str, str] | None = None,
) -> GatewayTeamIdentityResolver | MisconfiguredGatewayTeamIdentityResolver | None:
    env_source = os.environ if env is None else env
    cfg = config if isinstance(config, Mapping) else {}
    gateway_cfg = cfg.get("gateway") if isinstance(cfg.get("gateway"), Mapping) else {}
    team_identity_cfg = (
        gateway_cfg.get("team_identity")
        if isinstance(gateway_cfg.get("team_identity"), Mapping)
        else cfg.get("team_identity")
    )
    if not isinstance(team_identity_cfg, Mapping):
        team_identity_cfg = {}

    env_enabled = env_source.get("HERMES_GATEWAY_TEAM_IDENTITY_ENABLED")
    configured_enabled = team_identity_cfg.get("enabled")
    url = (
        _clean(env_source.get("HERMES_TEAM_CLOUD_URL"))
        or _clean(team_identity_cfg.get("team_cloud_url"))
        or _clean(team_identity_cfg.get("url"))
    )
    token = (
        _clean(env_source.get("HERMES_TEAM_CLOUD_SERVICE_TOKEN"))
        or _clean(env_source.get("TEAM_CLOUD_SERVICE_TOKEN"))
        or _clean(team_identity_cfg.get("service_token"))
    )
    enabled = is_truthy_value(
        env_enabled if env_enabled is not None else configured_enabled,
        default=bool(url or token),
    )
    if not enabled:
        return None
    if not url or not token:
        return MisconfiguredGatewayTeamIdentityResolver("team_identity_not_configured")
    return GatewayTeamIdentityResolver(team_cloud_url=url, service_token=token)
