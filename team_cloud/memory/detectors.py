"""Duplicate and contradiction detectors for memory review items."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Protocol


class SimilarityProvider(Protocol):
    def similarity(self, left: str, right: str) -> float: ...


class ContradictionProvider(Protocol):
    def contradiction(self, left: str, right: str) -> str | None: ...


class MemoryDuplicateConflictDetector:
    def __init__(
        self,
        *,
        review_repository: Any,
        memory_service: Any,
        similarity_provider: SimilarityProvider | None = None,
        contradiction_provider: ContradictionProvider | None = None,
        semantic_duplicate_threshold: float = 0.92,
    ) -> None:
        self.review_repository = review_repository
        self.memory_service = memory_service
        self.similarity_provider = similarity_provider
        self.contradiction_provider = contradiction_provider
        self.semantic_duplicate_threshold = semantic_duplicate_threshold

    def process_pending(self, *, limit: int = 100) -> dict[str, int]:
        items = [
            item
            for item in self.review_repository.review_items.values()
            if item.status == "pending"
        ][:limit]
        summary = {
            "selected": len(items),
            "duplicates": 0,
            "conflicts": 0,
            "unchanged": 0,
        }
        for item in items:
            candidate = self.memory_service.items.get(item.memory_id)
            if candidate is None:
                summary["unchanged"] += 1
                continue
            existing_memories = _matching_active_memories(
                self.memory_service.items.values(),
                candidate=candidate,
            )
            result = self._classify(candidate, existing_memories)
            if result is None:
                summary["unchanged"] += 1
                continue
            kind, reason, payload = result
            updated = replace(
                item,
                review_kind=kind,
                reason=reason,
                candidate_payload={**item.candidate_payload, **payload},
            )
            self.review_repository.review_items[item.id] = updated
            summary["duplicates" if kind == "duplicate" else "conflicts"] += 1
        return summary

    def _classify(
        self,
        candidate: dict[str, Any],
        existing_memories: tuple[dict[str, Any], ...],
    ) -> tuple[str, str, dict[str, Any]] | None:
        for existing in existing_memories:
            if existing["checksum_sha256"] == candidate["checksum_sha256"]:
                return (
                    "duplicate",
                    "checksum_duplicate",
                    {"duplicate_memory_id": existing["id"]},
                )
        if self.similarity_provider is not None:
            for existing in existing_memories:
                score = self.similarity_provider.similarity(
                    candidate["normalized_content"],
                    existing["normalized_content"],
                )
                if score >= self.semantic_duplicate_threshold:
                    return (
                        "duplicate",
                        "semantic_duplicate",
                        {
                            "duplicate_memory_id": existing["id"],
                            "duplicate_score": score,
                        },
                    )
        if self.contradiction_provider is not None:
            for existing in existing_memories:
                reason = self.contradiction_provider.contradiction(
                    candidate["normalized_content"],
                    existing["normalized_content"],
                )
                if reason:
                    return (
                        "conflict",
                        "contradiction",
                        {
                            "conflict_memory_id": existing["id"],
                            "conflict_reason": reason,
                        },
                    )
        return None


def _matching_active_memories(
    memories,
    *,
    candidate: dict[str, Any],
) -> tuple[dict[str, Any], ...]:
    matches = []
    for memory in memories:
        if memory["id"] == candidate["id"]:
            continue
        if memory["org_id"] != candidate["org_id"]:
            continue
        if memory["scope"] != candidate["scope"]:
            continue
        if memory["status"] != "active":
            continue
        if memory.get("team_id") != candidate.get("team_id"):
            continue
        if memory.get("project_id") != candidate.get("project_id"):
            continue
        matches.append(memory)
    return tuple(matches)
