"""External identity resolution primitives for Team Cloud."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import quote


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _session_component(value: str) -> str:
    return quote(value, safe="")


def team_session_key_prefix(*, org_id: str, team_id: str) -> str:
    if not org_id or not team_id:
        raise ValueError("org_id and team_id are required")
    return f"team:{_session_component(org_id)}:{_session_component(team_id)}"


@dataclass(frozen=True)
class ExternalIdentityBinding:
    platform: str
    external_user_id: str
    org_id: str
    team_id: str
    member_id: str
    project_id: str | None = None
    external_team_id: str | None = None
    external_channel_id: str | None = None
    status: str = "active"


class InMemoryExternalIdentityResolver:
    """Small in-memory resolver used by local smoke tests and dev wiring."""

    def __init__(self) -> None:
        self.bindings: dict[tuple[str, str, str], ExternalIdentityBinding] = {}

    def bind(
        self,
        *,
        platform: str,
        external_user_id: str,
        org_id: str,
        team_id: str,
        member_id: str,
        project_id: str | None = None,
        external_team_id: str | None = None,
        external_channel_id: str | None = None,
        status: str = "active",
    ) -> ExternalIdentityBinding:
        binding = ExternalIdentityBinding(
            platform=_clean(platform).lower(),
            external_user_id=_clean(external_user_id),
            org_id=_clean(org_id),
            team_id=_clean(team_id),
            member_id=_clean(member_id),
            project_id=_clean(project_id) or None,
            external_team_id=_clean(external_team_id) or None,
            external_channel_id=_clean(external_channel_id) or None,
            status=_clean(status).lower() or "active",
        )
        if not binding.platform or not binding.external_user_id:
            raise ValueError("platform and external_user_id are required")
        if not binding.org_id or not binding.team_id or not binding.member_id:
            raise ValueError("org_id, team_id, and member_id are required")
        self.bindings[self._key(binding.platform, binding.external_user_id, binding.external_team_id)] = binding
        return binding

    def resolve(self, payload: dict[str, Any]) -> dict[str, Any]:
        platform = _clean(payload.get("platform")).lower()
        external_user_id = _clean(payload.get("external_user_id"))
        external_team_id = _clean(payload.get("external_team_id")) or None
        shared_session = bool(payload.get("shared_session"))
        if not platform or not external_user_id:
            return self._unbound(platform=platform, external_user_id=external_user_id)

        binding = self.bindings.get(self._key(platform, external_user_id, external_team_id))
        if binding is None and external_team_id:
            binding = self.bindings.get(self._key(platform, external_user_id, None))
        if binding is None or binding.status != "active":
            return self._unbound(platform=platform, external_user_id=external_user_id)

        team_context = {
            "org_id": binding.org_id,
            "team_id": binding.team_id,
            "project_id": binding.project_id,
            "member_id": binding.member_id,
            "personal_memory_enabled": not shared_session,
        }
        return {
            "status": "resolved",
            "team_context": team_context,
            "session_key_prefix": team_session_key_prefix(
                org_id=binding.org_id,
                team_id=binding.team_id,
            ),
            "binding_message": None,
        }

    @staticmethod
    def _key(platform: str, external_user_id: str, external_team_id: str | None) -> tuple[str, str, str]:
        return (platform, external_user_id, external_team_id or "")

    @staticmethod
    def _unbound(*, platform: str, external_user_id: str) -> dict[str, Any]:
        return {
            "status": "unbound",
            "team_context": None,
            "session_key_prefix": None,
            "binding_message": (
                "This platform account is not bound to Hermes Team Cloud yet. "
                "Generate a gateway binding code in Team Cloud, then send the "
                f"binding code from {platform or 'this platform'} as {external_user_id or 'this user'}."
            ),
        }
