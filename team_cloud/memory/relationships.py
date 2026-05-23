"""Memory relationship planning and outbox enqueueing."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from team_cloud.authz.outbox import (
    InMemoryRelationshipOutboxRepository,
    RelationshipOutboxItem,
    RelationshipOutboxService,
)


class MemoryRelationshipService:
    def __init__(
        self,
        *,
        outbox_repository: InMemoryRelationshipOutboxRepository | None = None,
        outbox_service: RelationshipOutboxService | None = None,
    ) -> None:
        if outbox_service is None:
            if outbox_repository is None:
                raise ValueError("memory relationships require an outbox repository")
            outbox_service = RelationshipOutboxService(outbox_repository)
        self.outbox_service = outbox_service

    def enqueue_memory_relationships(
        self,
        memory: Mapping[str, Any],
        *,
        reviewer_member_ids: Iterable[str] = (),
    ) -> RelationshipOutboxItem:
        relationships = memory_relationships(
            memory,
            reviewer_member_ids=reviewer_member_ids,
        )
        return self.outbox_service.enqueue(
            org_id=_require(memory, "org_id", "memory relationship requires org_id"),
            aggregate_type="memory",
            aggregate_id=_require(memory, "id", "memory relationship requires id"),
            operation="touch",
            relationships=relationships,
        )


def memory_relationships(
    memory: Mapping[str, Any],
    *,
    reviewer_member_ids: Iterable[str] = (),
) -> tuple[str, ...]:
    memory_id = _require(memory, "id", "memory relationship requires id")
    scope = _require(memory, "scope", "memory relationship requires scope")
    relationships: list[str] = []
    if scope == "personal":
        subject_member_id = _require(
            memory,
            "subject_member_id",
            "personal memory relationship requires subject_member_id",
        )
        relationships.append(f"memory:{memory_id}#owner@user:{subject_member_id}")
        return tuple(relationships)
    if scope == "team_shared":
        team_id = _require(
            memory,
            "team_id",
            "team_shared memory relationship requires team_id",
        )
        project_id = memory.get("project_id")
        if project_id:
            relationships.append(f"memory:{memory_id}#parent_project@project:{project_id}")
        relationships.append(f"memory:{memory_id}#parent_team@team:{team_id}")
        for reviewer_member_id in _unique_ids(reviewer_member_ids):
            relationships.append(f"memory:{memory_id}#curator@user:{reviewer_member_id}")
        return tuple(relationships)
    raise ValueError("scope must be personal or team_shared")


def _unique_ids(values: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = str(value).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return tuple(result)


def _require(memory: Mapping[str, Any], field_name: str, message: str) -> str:
    value = memory.get(field_name)
    if value is None or value == "":
        raise ValueError(message)
    return str(value)
