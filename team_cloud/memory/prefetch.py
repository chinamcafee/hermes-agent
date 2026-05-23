"""Memory prefetch pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from .query import MemoryItem, MemoryQueryService


class EmbeddingProvider(Protocol):
    def embed(self, text: str) -> tuple[float, ...]: ...


@dataclass(frozen=True)
class StaticEmbeddingProvider:
    embedding: tuple[float, ...]

    def embed(self, text: str) -> tuple[float, ...]:
        return self.embedding


class MemoryPrefetchPipeline:
    def __init__(
        self,
        *,
        embedding_provider: EmbeddingProvider,
        query_service: MemoryQueryService,
    ):
        self.embedding_provider = embedding_provider
        self.query_service = query_service

    def prefetch(
        self,
        *,
        query: str,
        org_id: str,
        member_id: str,
        team_id: str,
        project_id: str | None = None,
        limit: int = 8,
        include_personal: bool = True,
    ) -> dict[str, object]:
        query_embedding = self.embedding_provider.embed(query)
        personal = (
            self.query_service.query_personal(
                org_id=org_id,
                member_id=member_id,
                query_embedding=query_embedding,
                limit=limit,
            )
            if include_personal
            else None
        )
        team = self.query_service.query_team(
            org_id=org_id,
            team_id=team_id,
            project_id=project_id,
            subject_type="user",
            subject_id=member_id,
            query_embedding=query_embedding,
            limit=limit,
        )
        partitions = [
            _partition("personal", personal.items if personal is not None else ()),
            _partition("team_shared", team.items),
        ]
        memory_ids = [
            *(personal.read_memory_ids if personal is not None else ()),
            *team.read_memory_ids,
        ]
        return {
            "query": query,
            "partitions": partitions,
            "memory_ids": memory_ids,
        }


def _partition(scope: str, items: Sequence[MemoryItem]) -> dict[str, object]:
    return {
        "scope": scope,
        "items": [_serialize_item(item) for item in items],
        "memory_ids": [item.id for item in items],
    }


def _serialize_item(item: MemoryItem) -> dict[str, object]:
    return {
        "id": item.id,
        "scope": item.scope,
        "memory_type": item.memory_type,
        "sensitivity": item.sensitivity,
        "content": item.content,
    }
