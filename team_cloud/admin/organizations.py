"""Organization, team, and member management primitives."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from team_cloud.authz.outbox import (
    InMemoryRelationshipOutboxRepository,
    RelationshipOutboxService,
)


class OrganizationNotFound(KeyError):
    """Raised when an organization does not exist."""


class MemberNotFound(KeyError):
    """Raised when a member does not exist."""


@dataclass
class InMemoryOrganizationService:
    outbox_repository: InMemoryRelationshipOutboxRepository
    organizations: dict[str, dict[str, Any]] = field(default_factory=dict)
    teams: dict[tuple[str, str], dict[str, Any]] = field(default_factory=dict)
    members: dict[tuple[str, str], dict[str, Any]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.outbox = RelationshipOutboxService(self.outbox_repository)

    def create_organization(self, *, slug: str, name: str) -> dict[str, Any]:
        organization = {
            "id": slug,
            "slug": slug,
            "name": name,
            "status": "active",
        }
        self.organizations[slug] = organization
        return organization

    def list_organizations(self) -> list[dict[str, Any]]:
        return list(self.organizations.values())

    def create_team(self, *, org_id: str, slug: str, name: str) -> dict[str, Any]:
        self._require_org(org_id)
        team = {
            "id": f"{org_id}:{slug}",
            "org_id": org_id,
            "slug": slug,
            "name": name,
            "status": "active",
        }
        self.teams[(org_id, team["id"])] = team
        return team

    def list_teams(self, *, org_id: str) -> list[dict[str, Any]]:
        self._require_org(org_id)
        return [team for (team_org_id, _), team in self.teams.items() if team_org_id == org_id]

    def list_members(self, *, org_id: str) -> list[dict[str, Any]]:
        self._require_org(org_id)
        return [
            member
            for (member_org_id, _), member in self.members.items()
            if member_org_id == org_id
        ]

    def invite_member(
        self,
        *,
        org_id: str,
        email: str,
        display_name: str,
        user_id: str,
        role: str = "member",
    ) -> dict[str, Any]:
        self._require_org(org_id)
        member = {
            "id": f"{org_id}:{user_id}",
            "org_id": org_id,
            "user_id": user_id,
            "email": email,
            "display_name": display_name,
            "role": role,
            "status": "invited",
        }
        self.members[(org_id, member["id"])] = member
        return member

    def disable_member(self, *, org_id: str, member_id: str) -> dict[str, Any]:
        key = (org_id, member_id)
        if key not in self.members:
            raise MemberNotFound(member_id)
        member = {**self.members[key], "status": "suspended"}
        self.members[key] = member
        self.outbox.enqueue(
            org_id=org_id,
            aggregate_type="member",
            aggregate_id=member_id,
            operation="delete",
            relationships=[f"organization:{org_id}#member@user:{member['user_id']}"],
        )
        return member

    def _require_org(self, org_id: str) -> None:
        if org_id not in self.organizations:
            raise OrganizationNotFound(org_id)
