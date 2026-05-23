"""Relationship outbox primitives for SpiceDB writes."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
import hashlib
from typing import Any, Iterable, Literal, Protocol
from uuid import uuid4

from .spicedb import Relationship


OutboxOperation = Literal["touch", "create", "delete"]
OutboxStatus = Literal["pending", "processing", "applied", "failed", "dead_letter"]


class RelationshipWriter(Protocol):
    def write_relationships(
        self,
        *,
        relationships: list[str],
        operation: str,
    ) -> dict[str, Any]: ...


@dataclass(frozen=True)
class RelationshipOutboxItem:
    id: str
    org_id: str
    aggregate_type: str
    aggregate_id: str
    idempotency_key: str
    operation: OutboxOperation
    relationships: tuple[str, ...]
    status: OutboxStatus = "pending"
    attempts: int = 0
    last_error: str | None = None
    created_at: datetime | None = None
    processed_at: datetime | None = None


class InMemoryRelationshipOutboxRepository:
    def __init__(self) -> None:
        self.items: dict[str, RelationshipOutboxItem] = {}
        self._ids_by_idempotency_key: dict[str, str] = {}

    def enqueue(self, item: RelationshipOutboxItem) -> RelationshipOutboxItem:
        existing_id = self._ids_by_idempotency_key.get(item.idempotency_key)
        if existing_id is not None:
            return self.items[existing_id]
        self.items[item.id] = item
        self._ids_by_idempotency_key[item.idempotency_key] = item.id
        return item

    def next_pending(self, *, limit: int) -> tuple[RelationshipOutboxItem, ...]:
        candidates = [
            item
            for item in self.items.values()
            if item.status in {"pending", "failed"}
        ]
        candidates.sort(key=lambda item: item.created_at or datetime.min.replace(tzinfo=UTC))
        return tuple(candidates[:limit])

    def mark_processing(self, item_id: str) -> RelationshipOutboxItem:
        item = replace(self.items[item_id], status="processing", last_error=None)
        self.items[item_id] = item
        return item

    def mark_applied(
        self,
        item_id: str,
        *,
        processed_at: datetime | None = None,
    ) -> RelationshipOutboxItem:
        item = replace(
            self.items[item_id],
            status="applied",
            last_error=None,
            processed_at=processed_at or _utcnow(),
        )
        self.items[item_id] = item
        return item

    def mark_failed(
        self,
        item_id: str,
        *,
        attempts: int,
        error: str,
        dead_letter: bool,
    ) -> RelationshipOutboxItem:
        item = replace(
            self.items[item_id],
            status="dead_letter" if dead_letter else "failed",
            attempts=attempts,
            last_error=error,
        )
        self.items[item_id] = item
        return item


class RelationshipOutboxService:
    def __init__(self, repository: InMemoryRelationshipOutboxRepository):
        self.repository = repository

    def enqueue(
        self,
        *,
        org_id: str,
        aggregate_type: str,
        aggregate_id: str,
        operation: OutboxOperation,
        relationships: Iterable[Relationship | str],
        idempotency_key: str | None = None,
        created_at: datetime | None = None,
    ) -> RelationshipOutboxItem:
        serialized_relationships = _serialize_relationships(relationships)
        key = idempotency_key or _idempotency_key(
            org_id=org_id,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            operation=operation,
            relationships=serialized_relationships,
        )
        item = RelationshipOutboxItem(
            id=f"outbox_{uuid4().hex}",
            org_id=org_id,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            idempotency_key=key,
            operation=operation,
            relationships=serialized_relationships,
            created_at=created_at or _utcnow(),
        )
        return self.repository.enqueue(item)

    def requires_fail_closed(self, *, aggregate_type: str, aggregate_id: str) -> bool:
        return bool(
            self.fail_closed_items(
                aggregate_type=aggregate_type,
                aggregate_id=aggregate_id,
            )
        )

    def fail_closed_items(
        self,
        *,
        aggregate_type: str,
        aggregate_id: str,
    ) -> tuple[RelationshipOutboxItem, ...]:
        return tuple(
            item
            for item in self.repository.items.values()
            if item.aggregate_type == aggregate_type
            and item.aggregate_id == aggregate_id
            and item.status != "applied"
        )

    def fail_closed_status(
        self,
        *,
        aggregate_type: str,
        aggregate_id: str,
        now: datetime | None = None,
        lag_after: timedelta | None = None,
    ) -> dict[str, Any]:
        reference_time = now or _utcnow()
        lag_threshold = lag_after or timedelta(minutes=5)
        items = self.fail_closed_items(
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
        )
        reasons: list[str] = []
        item_payloads = []
        for item in items:
            age_seconds = _age_seconds(reference_time, item.created_at)
            if item.status == "dead_letter":
                reasons.append("relationship_outbox_dead_letter")
            else:
                reasons.append("relationship_outbox_pending")
                if age_seconds >= int(lag_threshold.total_seconds()):
                    reasons.append("relationship_outbox_lag")
            item_payloads.append(
                {
                    "id": item.id,
                    "status": item.status,
                    "aggregate_type": item.aggregate_type,
                    "aggregate_id": item.aggregate_id,
                    "operation": item.operation,
                    "attempts": item.attempts,
                    "age_seconds": age_seconds,
                    "last_error": item.last_error,
                }
            )
        return {
            "blocked": bool(items),
            "reasons": tuple(_dedupe(reasons)),
            "items": tuple(item_payloads),
        }


class RelationshipOutboxWorker:
    def __init__(
        self,
        *,
        repository: InMemoryRelationshipOutboxRepository,
        relationship_writer: RelationshipWriter,
        max_attempts: int = 5,
    ) -> None:
        self.repository = repository
        self.relationship_writer = relationship_writer
        self.max_attempts = max_attempts

    def process_pending(self, *, limit: int = 100) -> dict[str, int]:
        summary = {"processed": 0, "applied": 0, "failed": 0, "dead_letter": 0}
        for item in self.repository.next_pending(limit=limit):
            self.repository.mark_processing(item.id)
            summary["processed"] += 1
            try:
                self.relationship_writer.write_relationships(
                    relationships=list(item.relationships),
                    operation=item.operation,
                )
            except Exception as exc:
                attempts = item.attempts + 1
                dead_letter = attempts >= self.max_attempts
                self.repository.mark_failed(
                    item.id,
                    attempts=attempts,
                    error=str(exc),
                    dead_letter=dead_letter,
                )
                summary["dead_letter" if dead_letter else "failed"] += 1
                continue
            self.repository.mark_applied(item.id)
            summary["applied"] += 1
        return summary


def _serialize_relationships(
    relationships: Iterable[Relationship | str],
) -> tuple[str, ...]:
    serialized = []
    for relationship in relationships:
        if isinstance(relationship, Relationship):
            serialized.append(relationship.as_spicedb())
        else:
            serialized.append(str(relationship))
    if not serialized:
        raise ValueError("relationship outbox item requires at least one relationship")
    return tuple(serialized)


def _idempotency_key(
    *,
    org_id: str,
    aggregate_type: str,
    aggregate_id: str,
    operation: str,
    relationships: tuple[str, ...],
) -> str:
    payload = "|".join(
        [org_id, aggregate_type, aggregate_id, operation, *sorted(relationships)]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _age_seconds(now: datetime, created_at: datetime | None) -> int:
    if created_at is None:
        return 0
    return max(0, int((now - created_at).total_seconds()))


def _dedupe(values: Iterable[str]) -> tuple[str, ...]:
    seen = set()
    result = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return tuple(result)
