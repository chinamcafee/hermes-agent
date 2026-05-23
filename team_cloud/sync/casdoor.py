"""Casdoor directory synchronization service layer."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
import re
from typing import Any, Protocol


SENSITIVE_KEY_PARTS = ("token", "secret", "password", "credential")


class CasdoorDirectoryClient(Protocol):
    def list_organizations(self) -> list[dict[str, Any]]: ...

    def list_groups(self) -> list[dict[str, Any]]: ...

    def list_users(self) -> list[dict[str, Any]]: ...


@dataclass(frozen=True)
class SyncCommand:
    action: str
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"action": self.action, "payload": _sanitize(self.payload)}


@dataclass(frozen=True)
class SyncResult:
    commands: tuple[SyncCommand, ...] = field(default_factory=tuple)

    @property
    def counts(self) -> dict[str, int]:
        counter: Counter[str] = Counter()
        for command in self.commands:
            bucket = _COUNT_BUCKETS.get(command.action)
            if bucket:
                counter[bucket] += 1
        return dict(counter)

    def to_dict(self) -> dict[str, Any]:
        return {
            "counts": self.counts,
            "commands": [command.to_dict() for command in self.commands],
        }


_COUNT_BUCKETS = {
    "upsert_user": "users",
    "upsert_organization": "organizations",
    "upsert_member": "members",
    "upsert_external_identity": "external_identities",
    "upsert_team": "teams",
    "upsert_team_membership": "team_memberships",
    "record_audit": "audit_events",
    "enqueue_spicedb_relationship_touch": "spicedb_outbox",
    "enqueue_spicedb_relationship_delete": "spicedb_outbox",
}


class InMemoryCasdoorSyncRepository:
    """Small repository implementation used by tests and local dry-runs."""

    def __init__(self) -> None:
        self.users: dict[str, dict[str, Any]] = {}
        self.organizations: dict[str, dict[str, Any]] = {}
        self.members: dict[tuple[str, str], dict[str, Any]] = {}
        self.teams: dict[tuple[str, str], dict[str, Any]] = {}
        self.team_memberships: set[tuple[str, str, str]] = set()
        self.external_identities: dict[tuple[str, str, str], dict[str, Any]] = {}
        self.spicedb_outbox: list[dict[str, Any]] = []
        self.audit_events: list[dict[str, Any]] = []
        self.revoked_sessions: list[dict[str, str]] = []
        self.pending_pat_revocations: list[dict[str, str]] = []

    def upsert_organization(self, *, slug: str, name: str, status: str) -> SyncCommand:
        self.organizations[slug] = {
            "id": f"org:{slug}",
            "slug": slug,
            "name": name,
            "status": status,
        }
        return SyncCommand("upsert_organization", self.organizations[slug])

    def upsert_user(
        self,
        *,
        subject: str,
        email: str,
        display_name: str,
        avatar_url: str = "",
        status: str = "active",
    ) -> SyncCommand:
        self.users[subject] = {
            "id": f"user:{subject}",
            "casdoor_subject": subject,
            "primary_email": email,
            "display_name": display_name,
            "avatar_url": avatar_url,
            "status": status,
        }
        return SyncCommand("upsert_user", self.users[subject])

    def upsert_member(
        self,
        *,
        org_slug: str,
        subject: str,
        status: str,
    ) -> SyncCommand:
        member = {
            "id": f"member:{org_slug}:{subject}",
            "org_slug": org_slug,
            "subject": subject,
            "status": status,
        }
        self.members[(org_slug, subject)] = member
        return SyncCommand("upsert_member", member)

    def upsert_external_identity(
        self,
        *,
        org_slug: str,
        subject: str,
        metadata: dict[str, Any],
        status: str = "active",
    ) -> SyncCommand:
        identity = {
            "platform": "casdoor",
            "external_user_id": subject,
            "external_team_id": org_slug,
            "metadata": _sanitize(metadata),
            "status": status,
        }
        self.external_identities[("casdoor", subject, org_slug)] = identity
        return SyncCommand("upsert_external_identity", identity)

    def upsert_team(self, *, org_slug: str, slug: str, name: str) -> SyncCommand:
        team = {
            "id": f"team:{org_slug}:{slug}",
            "org_slug": org_slug,
            "slug": slug,
            "name": name,
            "status": "active",
        }
        self.teams[(org_slug, slug)] = team
        return SyncCommand("upsert_team", team)

    def upsert_team_membership(
        self,
        *,
        org_slug: str,
        team_slug: str,
        subject: str,
    ) -> SyncCommand:
        membership = (org_slug, team_slug, subject)
        self.team_memberships.add(membership)
        return SyncCommand(
            "upsert_team_membership",
            {
                "org_slug": org_slug,
                "team_slug": team_slug,
                "subject": subject,
            },
        )

    def revoke_active_sessions(self, *, org_slug: str, subject: str) -> SyncCommand:
        payload = {"org_slug": org_slug, "subject": subject}
        self.revoked_sessions.append(payload)
        return SyncCommand("revoke_active_sessions", payload)

    def mark_pat_revocation_pending(self, *, org_slug: str, subject: str) -> SyncCommand:
        payload = {"org_slug": org_slug, "subject": subject}
        self.pending_pat_revocations.append(payload)
        return SyncCommand("mark_pat_revocation_pending", payload)

    def enqueue_spicedb_relationship_touch(
        self,
        *,
        org_slug: str,
        aggregate_type: str,
        aggregate_id: str,
        relationships: list[str],
    ) -> SyncCommand:
        return self._enqueue_spicedb_relationships(
            org_slug=org_slug,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            operation="touch",
            relationships=relationships,
        )

    def enqueue_spicedb_relationship_delete(
        self,
        *,
        org_slug: str,
        aggregate_type: str,
        aggregate_id: str,
        relationships: list[str],
    ) -> SyncCommand:
        return self._enqueue_spicedb_relationships(
            org_slug=org_slug,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            operation="delete",
            relationships=relationships,
        )

    def record_audit(
        self,
        *,
        action: str,
        org_slug: str | None = None,
        subject: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SyncCommand:
        event = {
            "actor_type": "system",
            "action": action,
            "org_slug": org_slug,
            "subject": subject,
            "metadata": _sanitize(metadata or {}),
        }
        self.audit_events.append(event)
        return SyncCommand("record_audit", event)

    def _enqueue_spicedb_relationships(
        self,
        *,
        org_slug: str,
        aggregate_type: str,
        aggregate_id: str,
        operation: str,
        relationships: list[str],
    ) -> SyncCommand:
        outbox_item = {
            "org_slug": org_slug,
            "aggregate_type": aggregate_type,
            "aggregate_id": aggregate_id,
            "operation": operation,
            "relationships": relationships,
            "status": "pending",
        }
        self.spicedb_outbox.append(outbox_item)
        return SyncCommand(
            f"enqueue_spicedb_relationship_{operation}",
            outbox_item,
        )


class CasdoorSyncWorker:
    def __init__(
        self,
        *,
        casdoor_client: CasdoorDirectoryClient | None = None,
        repository: InMemoryCasdoorSyncRepository | None = None,
    ) -> None:
        self.casdoor_client = casdoor_client
        self.repository = repository or InMemoryCasdoorSyncRepository()

    def lazy_upsert_from_claims(self, claims: dict[str, Any]) -> SyncResult:
        org_slug = _slug(str(claims.get("organization") or claims.get("owner") or "default"))
        subject = _required_text(claims, "sub")
        email = str(claims.get("email") or f"{subject}@unknown.local")
        display_name = str(claims.get("name") or claims.get("preferred_username") or subject)
        groups = _normalize_groups(claims.get("groups"))
        commands = self._upsert_identity(
            org_slug=org_slug,
            subject=subject,
            email=email,
            display_name=display_name,
            avatar_url=str(claims.get("picture") or ""),
            status="active",
            groups=groups,
            metadata=claims,
        )
        commands.append(
            self.repository.record_audit(
                action="casdoor.lazy_upsert",
                org_slug=org_slug,
                subject=subject,
                metadata={"groups": groups, "roles": claims.get("roles", [])},
            )
        )
        return SyncResult(tuple(commands))

    def reconcile(self) -> SyncResult:
        if self.casdoor_client is None:
            raise RuntimeError("casdoor_client is required for reconcile")

        commands: list[SyncCommand] = []
        for organization in self.casdoor_client.list_organizations():
            commands.extend(self.sync_organization(organization).commands)
        for group in self.casdoor_client.list_groups():
            commands.extend(self.sync_group(group).commands)
        for user in self.casdoor_client.list_users():
            commands.extend(
                self._sync_user(
                    user,
                    ensure_organization=False,
                    ensure_teams=False,
                ).commands
            )
        commands.append(
            self.repository.record_audit(
                action="casdoor.reconcile",
                metadata={"source": "scheduled_reconcile"},
            )
        )
        return SyncResult(tuple(commands))

    def sync_organization(self, organization: dict[str, Any]) -> SyncResult:
        slug = _payload_slug(organization)
        name = _display_name(organization, fallback=slug)
        status = "suspended" if _is_disabled(organization) else "active"
        command = self.repository.upsert_organization(
            slug=slug,
            name=name,
            status=status,
        )
        return SyncResult((command,))

    def sync_group(self, group: dict[str, Any]) -> SyncResult:
        org_slug = _slug(str(group.get("owner") or group.get("organization") or "default"))
        team_slug = _payload_slug(group)
        command = self.repository.upsert_team(
            org_slug=org_slug,
            slug=team_slug,
            name=_display_name(group, fallback=team_slug),
        )
        return SyncResult((command,))

    def sync_user(self, user: dict[str, Any]) -> SyncResult:
        return self._sync_user(user, ensure_organization=True, ensure_teams=True)

    def _sync_user(
        self,
        user: dict[str, Any],
        *,
        ensure_organization: bool,
        ensure_teams: bool,
    ) -> SyncResult:
        org_slug = _slug(str(user.get("owner") or user.get("organization") or "default"))
        subject = _subject(user)
        groups = _normalize_groups(user.get("groups"))
        status = "suspended" if _is_disabled(user) else "active"
        commands = self._upsert_identity(
            org_slug=org_slug,
            subject=subject,
            email=str(user.get("email") or f"{subject}@unknown.local"),
            display_name=_display_name(user, fallback=subject),
            avatar_url=str(user.get("avatar") or user.get("picture") or ""),
            status=status,
            groups=groups,
            metadata=user,
            ensure_organization=ensure_organization,
            ensure_teams=ensure_teams,
        )
        if status == "suspended":
            commands.extend(self._propagate_disabled_user(org_slug, subject, groups))
        return SyncResult(tuple(commands))

    def _upsert_identity(
        self,
        *,
        org_slug: str,
        subject: str,
        email: str,
        display_name: str,
        avatar_url: str,
        status: str,
        groups: list[str],
        metadata: dict[str, Any],
        ensure_organization: bool = True,
        ensure_teams: bool = True,
    ) -> list[SyncCommand]:
        commands: list[SyncCommand] = []
        if ensure_organization:
            commands.append(
                self.repository.upsert_organization(
                    slug=org_slug,
                    name=org_slug,
                    status="active",
                )
            )
        commands.extend(
            [
                self.repository.upsert_user(
                    subject=subject,
                    email=email,
                    display_name=display_name,
                    avatar_url=avatar_url,
                    status=status,
                ),
                self.repository.upsert_member(
                    org_slug=org_slug,
                    subject=subject,
                    status=status,
                ),
                self.repository.upsert_external_identity(
                    org_slug=org_slug,
                    subject=subject,
                    metadata=metadata,
                    status="revoked" if status == "suspended" else "active",
                ),
            ]
        )
        for team_slug in groups:
            if ensure_teams:
                commands.append(
                    self.repository.upsert_team(
                        org_slug=org_slug,
                        slug=team_slug,
                        name=team_slug,
                    )
                )
            commands.append(
                self.repository.upsert_team_membership(
                    org_slug=org_slug,
                    team_slug=team_slug,
                    subject=subject,
                )
            )
            if status == "active":
                commands.append(
                    self.repository.enqueue_spicedb_relationship_touch(
                        org_slug=org_slug,
                        aggregate_type="team",
                        aggregate_id=f"{org_slug}/{team_slug}",
                        relationships=[
                            f"team:{org_slug}/{team_slug}#member@user:{subject}"
                        ],
                    )
                )
        if status == "active":
            commands.append(
                self.repository.enqueue_spicedb_relationship_touch(
                    org_slug=org_slug,
                    aggregate_type="organization",
                    aggregate_id=org_slug,
                    relationships=[
                        f"organization:{org_slug}#member@user:{subject}"
                    ],
                )
            )
        return commands

    def _propagate_disabled_user(
        self,
        org_slug: str,
        subject: str,
        groups: list[str],
    ) -> list[SyncCommand]:
        relationships = [f"organization:{org_slug}#member@user:{subject}"]
        relationships.extend(
            f"team:{org_slug}/{team_slug}#member@user:{subject}"
            for team_slug in groups
        )
        return [
            SyncCommand(
                "propagate_disabled_user",
                {"org_slug": org_slug, "subject": subject, "groups": groups},
            ),
            self.repository.revoke_active_sessions(org_slug=org_slug, subject=subject),
            self.repository.mark_pat_revocation_pending(
                org_slug=org_slug,
                subject=subject,
            ),
            self.repository.enqueue_spicedb_relationship_delete(
                org_slug=org_slug,
                aggregate_type="member",
                aggregate_id=f"{org_slug}/{subject}",
                relationships=relationships,
            ),
            self.repository.record_audit(
                action="casdoor.user_disabled",
                org_slug=org_slug,
                subject=subject,
                metadata={"groups": groups},
            ),
        ]


def _required_text(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if value is None or str(value).strip() == "":
        raise ValueError(f"Casdoor payload missing required field: {key}")
    return str(value)


def _subject(payload: dict[str, Any]) -> str:
    for key in ("id", "sub", "name"):
        value = payload.get(key)
        if value:
            return str(value)
    raise ValueError("Casdoor user payload missing id/sub/name")


def _payload_slug(payload: dict[str, Any]) -> str:
    for key in ("slug", "name", "id"):
        value = payload.get(key)
        if value:
            return _slug(str(value))
    raise ValueError("Casdoor payload missing slug/name/id")


def _display_name(payload: dict[str, Any], *, fallback: str) -> str:
    return str(
        payload.get("displayName")
        or payload.get("display_name")
        or payload.get("name")
        or fallback
    )


def _is_disabled(payload: dict[str, Any]) -> bool:
    status = str(payload.get("status") or "").lower()
    return bool(
        payload.get("isForbidden")
        or payload.get("isDeleted")
        or payload.get("disabled")
        or status in {"disabled", "forbidden", "suspended", "deleted", "inactive"}
    )


def _normalize_groups(raw_groups: Any) -> list[str]:
    if raw_groups is None:
        return []
    if isinstance(raw_groups, str):
        raw_groups = [raw_groups]
    groups = []
    for group in raw_groups:
        if isinstance(group, dict):
            value = group.get("name") or group.get("id") or group.get("displayName")
        else:
            value = group
        if value:
            groups.append(_slug(str(value)))
    return sorted(set(groups))


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "default"


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized = {}
        for key, item in value.items():
            if any(part in str(key).lower() for part in SENSITIVE_KEY_PARTS):
                continue
            sanitized[key] = _sanitize(item)
        return sanitized
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_sanitize(item) for item in value)
    return value
