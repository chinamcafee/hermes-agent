"""Memory extraction worker primitives."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal, Protocol
from uuid import uuid4


@dataclass(frozen=True)
class MemoryExtractionCandidate:
    scope: Literal["personal", "team_shared"]
    content: str
    memory_type: str = "fact"
    sensitivity: str = "normal"
    confidence: float | None = None
    subject_member_id: str | None = None
    team_id: str | None = None
    project_id: str | None = None
    review_kind: str = "team_candidate"


@dataclass
class MemoryObservation:
    id: str
    org_id: str
    session_id: str | None
    member_id: str | None
    team_id: str | None
    project_id: str | None
    observation: dict[str, Any]
    status: str = "pending"
    extraction_trace: dict[str, Any] = field(default_factory=dict)
    confidence: float | None = None
    error: str | None = None
    created_at: str = field(default_factory=lambda: _now())
    processed_at: str | None = None


@dataclass(frozen=True)
class MemoryReviewItem:
    id: str
    org_id: str
    memory_id: str
    proposed_scope: str
    reviewer_member_id: str | None
    status: str
    reason: str | None
    review_kind: str
    candidate_payload: dict[str, Any]
    confidence: float | None
    created_at: str
    reviewed_at: str | None = None


class MemoryExtractor(Protocol):
    def extract(
        self,
        observation: MemoryObservation,
    ) -> Iterable[MemoryExtractionCandidate]: ...


class InMemoryMemoryObservationRepository:
    def __init__(self) -> None:
        self.observations: dict[str, MemoryObservation] = {}
        self.review_items: dict[str, MemoryReviewItem] = {}

    def create_observation(
        self,
        *,
        org_id: str,
        observation: dict[str, Any],
        session_id: str | None = None,
        member_id: str | None = None,
        team_id: str | None = None,
        project_id: str | None = None,
    ) -> MemoryObservation:
        item = MemoryObservation(
            id=f"obs_{uuid4().hex}",
            org_id=org_id,
            session_id=session_id,
            member_id=member_id,
            team_id=team_id,
            project_id=project_id,
            observation=dict(observation),
        )
        self.observations[item.id] = item
        return item

    def next_pending(self, *, limit: int) -> tuple[MemoryObservation, ...]:
        candidates = [
            observation
            for observation in self.observations.values()
            if observation.status == "pending"
        ]
        candidates.sort(key=lambda observation: observation.created_at)
        return tuple(candidates[:limit])

    def mark_processing(self, observation_id: str) -> MemoryObservation:
        observation = self.observations[observation_id]
        observation.status = "processing"
        observation.error = None
        return observation

    def mark_extracted(
        self,
        observation_id: str,
        *,
        extraction_trace: dict[str, Any],
        confidence: float | None,
    ) -> MemoryObservation:
        observation = self.observations[observation_id]
        observation.status = "extracted"
        observation.extraction_trace = extraction_trace
        observation.confidence = confidence
        observation.error = None
        observation.processed_at = _now()
        return observation

    def mark_ignored(
        self,
        observation_id: str,
        *,
        extraction_trace: dict[str, Any],
    ) -> MemoryObservation:
        observation = self.observations[observation_id]
        observation.status = "ignored"
        observation.extraction_trace = extraction_trace
        observation.error = None
        observation.processed_at = _now()
        return observation

    def mark_error(self, observation_id: str, *, error: str) -> MemoryObservation:
        observation = self.observations[observation_id]
        observation.status = "error"
        observation.error = error
        observation.processed_at = _now()
        return observation

    def create_review_item(
        self,
        *,
        org_id: str,
        memory_id: str,
        proposed_scope: str,
        reviewer_member_id: str | None,
        review_kind: str,
        candidate_payload: dict[str, Any],
        confidence: float | None,
        reason: str | None = None,
    ) -> MemoryReviewItem:
        item = MemoryReviewItem(
            id=f"review_{uuid4().hex}",
            org_id=org_id,
            memory_id=memory_id,
            proposed_scope=proposed_scope,
            reviewer_member_id=reviewer_member_id,
            status="pending",
            reason=reason,
            review_kind=review_kind,
            candidate_payload=candidate_payload,
            confidence=confidence,
            created_at=_now(),
        )
        self.review_items[item.id] = item
        return item


class MemoryExtractionWorker:
    def __init__(
        self,
        *,
        observation_repository: InMemoryMemoryObservationRepository,
        memory_service: Any,
        extractor: MemoryExtractor,
    ) -> None:
        self.observation_repository = observation_repository
        self.memory_service = memory_service
        self.extractor = extractor

    def process_pending(self, *, limit: int = 100) -> dict[str, int]:
        observations = self.observation_repository.next_pending(limit=limit)
        summary = {
            "selected": len(observations),
            "created_memories": 0,
            "review_items": 0,
            "ignored": 0,
            "failed": 0,
        }
        for observation in observations:
            self.observation_repository.mark_processing(observation.id)
            try:
                candidates = tuple(self.extractor.extract(observation))
            except Exception as exc:
                self.observation_repository.mark_error(
                    observation.id,
                    error=str(exc),
                )
                summary["failed"] += 1
                continue
            if not candidates:
                self.observation_repository.mark_ignored(
                    observation.id,
                    extraction_trace={"candidate_count": 0},
                )
                summary["ignored"] += 1
                continue
            created_memory_ids: list[str] = []
            review_item_ids: list[str] = []
            try:
                for candidate in candidates:
                    memory = self.memory_service.create_memory(
                        _memory_payload(observation, candidate)
                    )
                    created_memory_ids.append(memory["id"])
                    summary["created_memories"] += 1
                    if candidate.scope == "team_shared":
                        review_item = self.observation_repository.create_review_item(
                            org_id=observation.org_id,
                            memory_id=memory["id"],
                            proposed_scope="team_shared",
                            reviewer_member_id=None,
                            review_kind=candidate.review_kind,
                            candidate_payload=_candidate_payload(
                                observation,
                                candidate,
                                memory,
                            ),
                            confidence=candidate.confidence,
                        )
                        review_item_ids.append(review_item.id)
                        summary["review_items"] += 1
            except Exception as exc:
                self.observation_repository.mark_error(
                    observation.id,
                    error=str(exc),
                )
                summary["failed"] += 1
                continue
            self.observation_repository.mark_extracted(
                observation.id,
                extraction_trace={
                    "candidate_count": len(candidates),
                    "created_memory_ids": created_memory_ids,
                    "review_item_ids": review_item_ids,
                },
                confidence=_average_confidence(candidates),
            )
        return summary


def _memory_payload(
    observation: MemoryObservation,
    candidate: MemoryExtractionCandidate,
) -> dict[str, Any]:
    payload = {
        "org_id": observation.org_id,
        "scope": candidate.scope,
        "content": candidate.content,
        "memory_type": candidate.memory_type,
        "sensitivity": candidate.sensitivity,
        "created_by_member_id": observation.member_id,
        "source_type": "observation",
        "source_ref": {"observation_id": observation.id},
    }
    if candidate.scope == "personal":
        payload["subject_member_id"] = candidate.subject_member_id or observation.member_id
        return payload
    if candidate.scope == "team_shared":
        payload["team_id"] = candidate.team_id or observation.team_id
        payload["project_id"] = candidate.project_id or observation.project_id
        return payload
    raise ValueError("candidate scope must be personal or team_shared")


def _candidate_payload(
    observation: MemoryObservation,
    candidate: MemoryExtractionCandidate,
    memory: dict[str, Any],
) -> dict[str, Any]:
    return {
        "observation_id": observation.id,
        "memory_id": memory["id"],
        "scope": candidate.scope,
        "content": candidate.content,
        "memory_type": candidate.memory_type,
        "sensitivity": candidate.sensitivity,
        "confidence": candidate.confidence,
    }


def _average_confidence(candidates: tuple[MemoryExtractionCandidate, ...]) -> float | None:
    values = [candidate.confidence for candidate in candidates if candidate.confidence is not None]
    if not values:
        return None
    return sum(values) / len(values)


def _now() -> str:
    return datetime.now(UTC).isoformat()
