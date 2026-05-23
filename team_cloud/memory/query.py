"""Memory query layer primitives."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable, Literal, Sequence, cast

from team_cloud.authz.spicedb import PermissionCheck, ResourceRef, SubjectRef


@dataclass(frozen=True)
class MemoryItem:
    id: str
    org_id: str
    scope: Literal["personal", "team_shared"]
    subject_member_id: str | None
    team_id: str | None
    project_id: str | None
    status: str
    sensitivity: str
    memory_type: str
    content: str
    embedding: tuple[float, ...]


@dataclass(frozen=True)
class MemoryQueryResult:
    items: tuple[MemoryItem, ...]
    read_memory_ids: tuple[str, ...]


@dataclass(frozen=True)
class PgvectorQueryPlan:
    sql: str
    indexes: tuple[str, ...]
    post_filters: tuple[str, ...]


class InMemoryMemoryQueryRepository:
    def __init__(self, items: Iterable[MemoryItem] = ()):
        self.items = tuple(items)

    def query_personal(
        self,
        *,
        org_id: str,
        member_id: str,
        query_embedding: Sequence[float],
        limit: int,
    ) -> tuple[MemoryItem, ...]:
        candidates = (
            item
            for item in self.items
            if item.org_id == org_id
            and item.scope == "personal"
            and item.subject_member_id == member_id
            and item.status == "active"
        )
        return _rank(candidates, query_embedding=query_embedding, limit=limit)

    def query_team(
        self,
        *,
        org_id: str,
        team_id: str,
        project_id: str | None,
        query_embedding: Sequence[float],
        limit: int,
    ) -> tuple[MemoryItem, ...]:
        candidates = (
            item
            for item in self.items
            if item.org_id == org_id
            and item.scope == "team_shared"
            and item.team_id == team_id
            and item.status == "active"
            and (project_id is None or item.project_id == project_id)
        )
        return _rank(candidates, query_embedding=query_embedding, limit=limit)


class MemoryQueryService:
    def __init__(
        self,
        *,
        repository: InMemoryMemoryQueryRepository,
        authz_client=None,
    ):
        self.repository = repository
        self.authz_client = authz_client

    def query_personal(
        self,
        *,
        org_id: str,
        member_id: str,
        query_embedding: Sequence[float],
        limit: int,
    ) -> MemoryQueryResult:
        items = self.repository.query_personal(
            org_id=org_id,
            member_id=member_id,
            query_embedding=query_embedding,
            limit=limit,
        )
        return MemoryQueryResult(items=items, read_memory_ids=tuple(item.id for item in items))

    def query_team(
        self,
        *,
        org_id: str,
        team_id: str,
        project_id: str | None,
        subject_type: str,
        subject_id: str,
        query_embedding: Sequence[float],
        limit: int,
    ) -> MemoryQueryResult:
        candidates = self.repository.query_team(
            org_id=org_id,
            team_id=team_id,
            project_id=project_id,
            query_embedding=query_embedding,
            limit=limit,
        )
        if self.authz_client is None:
            return MemoryQueryResult(items=(), read_memory_ids=())

        subject = SubjectRef(_subject_type(subject_type), subject_id)
        checks = tuple(
            PermissionCheck(
                subject=subject,
                resource=ResourceRef("memory", item.id),
                permission="read_team",
            )
            for item in candidates
        )
        decisions = self.authz_client.batch_check(checks)
        allowed = tuple(
            item for item, decision in zip(candidates, decisions) if decision.allowed
        )
        return MemoryQueryResult(
            items=allowed,
            read_memory_ids=tuple(item.id for item in allowed),
        )


def explain_pgvector_query(*, scope: Literal["personal", "team_shared"]) -> PgvectorQueryPlan:
    common = """
select memory_items.*
from memory_items
join memory_embeddings on memory_embeddings.memory_id = memory_items.id
where memory_items.org_id = :org_id
  and memory_items.scope = :scope
  and memory_items.status = 'active'
order by memory_embeddings.embedding <=> :query_embedding
limit :limit
""".strip()
    indexes = (
        "idx_memory_embeddings_hnsw",
        "idx_memory_items_scope_type_status",
    )
    if scope == "personal":
        return PgvectorQueryPlan(
            sql=common.replace(
                "order by",
                "  and memory_items.subject_member_id = :member_id\norder by",
            ),
            indexes=indexes,
            post_filters=(),
        )
    return PgvectorQueryPlan(
        sql=common.replace(
            "order by",
            "  and memory_items.team_id = :team_id\n"
            "  and memory_items.project_id = :project_id\n"
            "order by",
        ),
        indexes=indexes,
        post_filters=("spicedb batch_check(memory#read_team)",),
    )


def _rank(
    items: Iterable[MemoryItem],
    *,
    query_embedding: Sequence[float],
    limit: int,
) -> tuple[MemoryItem, ...]:
    ranked = sorted(
        items,
        key=lambda item: _cosine_distance(item.embedding, query_embedding),
    )
    return tuple(ranked[:limit])


def _cosine_distance(left: Sequence[float], right: Sequence[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 1.0
    return 1.0 - (dot / (left_norm * right_norm))


def _subject_type(value: str) -> Literal["user", "service_account"]:
    if value not in {"user", "service_account"}:
        raise ValueError("subject_type must be user or service_account")
    return cast(Literal["user", "service_account"], value)
