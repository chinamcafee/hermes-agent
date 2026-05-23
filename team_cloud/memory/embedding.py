"""Memory embedding worker primitives."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import uuid4


class BatchEmbeddingProvider(Protocol):
    def embed_many(self, texts: Sequence[str]) -> tuple[tuple[float, ...], ...]: ...


@dataclass(frozen=True)
class MemoryEmbeddingRecord:
    id: str
    org_id: str
    memory_id: str
    embedding_model: str
    embedding_dim: int
    embedding: tuple[float, ...]
    checksum_sha256: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class MemoryEmbeddingFailure:
    memory_id: str
    embedding_model: str
    attempts: int
    last_error: str
    updated_at: str


class InMemoryMemoryEmbeddingRepository:
    def __init__(self, *, memory_service: Any):
        self.memory_service = memory_service
        self.embeddings: dict[tuple[str, str], MemoryEmbeddingRecord] = {}
        self.failures: dict[tuple[str, str], MemoryEmbeddingFailure] = {}

    def pending_memories(
        self,
        *,
        embedding_model: str,
        limit: int,
    ) -> tuple[dict[str, Any], ...]:
        candidates: list[dict[str, Any]] = []
        for memory in self.memory_service.items.values():
            if memory.get("status") not in {"active", "pending_review"}:
                continue
            current = self.get_embedding(
                memory_id=memory["id"],
                embedding_model=embedding_model,
            )
            if current is not None and current.checksum_sha256 == memory["checksum_sha256"]:
                continue
            candidates.append(dict(memory))
            if len(candidates) >= limit:
                break
        return tuple(candidates)

    def get_embedding(
        self,
        *,
        memory_id: str,
        embedding_model: str,
    ) -> MemoryEmbeddingRecord | None:
        return self.embeddings.get((memory_id, embedding_model))

    def upsert_embedding(
        self,
        *,
        memory: dict[str, Any],
        embedding_model: str,
        embedding: Sequence[float],
    ) -> MemoryEmbeddingRecord:
        key = (memory["id"], embedding_model)
        current = self.embeddings.get(key)
        now = _now()
        record = MemoryEmbeddingRecord(
            id=current.id if current is not None else f"emb_{uuid4().hex}",
            org_id=memory["org_id"],
            memory_id=memory["id"],
            embedding_model=embedding_model,
            embedding_dim=len(embedding),
            embedding=tuple(float(value) for value in embedding),
            checksum_sha256=memory["checksum_sha256"],
            created_at=current.created_at if current is not None else now,
            updated_at=now,
        )
        self.embeddings[key] = record
        self.failures.pop(key, None)
        return record

    def get_failure(
        self,
        *,
        memory_id: str,
        embedding_model: str,
    ) -> MemoryEmbeddingFailure | None:
        return self.failures.get((memory_id, embedding_model))

    def mark_failed(
        self,
        *,
        memory: dict[str, Any],
        embedding_model: str,
        error: str,
    ) -> MemoryEmbeddingFailure:
        key = (memory["id"], embedding_model)
        current = self.failures.get(key)
        failure = MemoryEmbeddingFailure(
            memory_id=memory["id"],
            embedding_model=embedding_model,
            attempts=(current.attempts if current is not None else 0) + 1,
            last_error=error,
            updated_at=_now(),
        )
        self.failures[key] = failure
        return failure


class MemoryEmbeddingWorker:
    def __init__(
        self,
        *,
        repository: InMemoryMemoryEmbeddingRepository,
        embedding_provider: BatchEmbeddingProvider,
        embedding_model: str,
        batch_size: int = 100,
        max_attempts: int = 5,
    ) -> None:
        if batch_size < 1:
            raise ValueError("batch_size must be positive")
        if max_attempts < 1:
            raise ValueError("max_attempts must be positive")
        self.repository = repository
        self.embedding_provider = embedding_provider
        self.embedding_model = embedding_model
        self.batch_size = batch_size
        self.max_attempts = max_attempts

    def process_pending(self, *, limit: int = 100) -> dict[str, int]:
        candidates = self.repository.pending_memories(
            embedding_model=self.embedding_model,
            limit=limit,
        )
        summary = {
            "selected": len(candidates),
            "embedded": 0,
            "failed": 0,
            "skipped": 0,
        }
        for batch in _chunks(candidates, self.batch_size):
            active_batch: list[dict[str, Any]] = []
            for memory in batch:
                failure = self.repository.get_failure(
                    memory_id=memory["id"],
                    embedding_model=self.embedding_model,
                )
                if failure is not None and failure.attempts >= self.max_attempts:
                    summary["skipped"] += 1
                    continue
                active_batch.append(memory)
            if not active_batch:
                continue
            texts = tuple(_embedding_text(memory) for memory in active_batch)
            try:
                embeddings = self.embedding_provider.embed_many(texts)
                if len(embeddings) != len(active_batch):
                    raise ValueError("embedding provider returned the wrong batch size")
            except Exception as exc:
                for memory in active_batch:
                    self.repository.mark_failed(
                        memory=memory,
                        embedding_model=self.embedding_model,
                        error=str(exc),
                    )
                    summary["failed"] += 1
                continue
            for memory, embedding in zip(active_batch, embeddings):
                self.repository.upsert_embedding(
                    memory=memory,
                    embedding_model=self.embedding_model,
                    embedding=embedding,
                )
                summary["embedded"] += 1
        return summary


def _chunks(
    values: Sequence[dict[str, Any]],
    size: int,
) -> tuple[tuple[dict[str, Any], ...], ...]:
    return tuple(tuple(values[index : index + size]) for index in range(0, len(values), size))


def _embedding_text(memory: dict[str, Any]) -> str:
    return str(memory.get("normalized_content") or memory["content"])


def _now() -> str:
    return datetime.now(UTC).isoformat()
