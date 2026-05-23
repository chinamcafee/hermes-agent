from __future__ import annotations


class FixedSimilarityProvider:
    def __init__(self, score: float):
        self.score = score
        self.calls = []

    def similarity(self, left: str, right: str) -> float:
        self.calls.append((left, right))
        return self.score


class FixedContradictionProvider:
    def __init__(self, reason: str | None = None):
        self.reason = reason
        self.calls = []

    def contradiction(self, left: str, right: str) -> str | None:
        self.calls.append((left, right))
        return self.reason


def _services():
    from team_cloud.memory.extraction import InMemoryMemoryObservationRepository
    from team_cloud.memory.service import InMemoryMemoryService

    return InMemoryMemoryService(), InMemoryMemoryObservationRepository()


def _seed_review(memory_service, review_repository, *, existing_content, candidate_content):
    existing = memory_service.create_memory(
        {
            "org_id": "org-1",
            "scope": "team_shared",
            "team_id": "team-1",
            "project_id": "project-1",
            "status": "active",
            "content": existing_content,
        }
    )
    candidate = memory_service.create_memory(
        {
            "org_id": "org-1",
            "scope": "team_shared",
            "team_id": "team-1",
            "project_id": "project-1",
            "content": candidate_content,
        }
    )
    review_item = review_repository.create_review_item(
        org_id="org-1",
        memory_id=candidate["id"],
        proposed_scope="team_shared",
        reviewer_member_id=None,
        review_kind="team_candidate",
        candidate_payload={"content": candidate_content},
        confidence=0.72,
    )
    return existing, candidate, review_item


def test_duplicate_detector_marks_checksum_duplicate_review():
    from team_cloud.memory.detectors import MemoryDuplicateConflictDetector

    memory_service, review_repository = _services()
    existing, _candidate, review_item = _seed_review(
        memory_service,
        review_repository,
        existing_content="Release checklist lives in docs/releases.md.",
        candidate_content="Release checklist lives in docs/releases.md.",
    )
    detector = MemoryDuplicateConflictDetector(
        review_repository=review_repository,
        memory_service=memory_service,
    )

    summary = detector.process_pending(limit=10)

    updated = review_repository.review_items[review_item.id]
    assert summary == {"selected": 1, "duplicates": 1, "conflicts": 0, "unchanged": 0}
    assert updated.review_kind == "duplicate"
    assert updated.reason == "checksum_duplicate"
    assert updated.candidate_payload["duplicate_memory_id"] == existing["id"]


def test_duplicate_detector_marks_semantic_duplicate_review():
    from team_cloud.memory.detectors import MemoryDuplicateConflictDetector

    memory_service, review_repository = _services()
    existing, _candidate, review_item = _seed_review(
        memory_service,
        review_repository,
        existing_content="Release checklist lives in docs/releases.md.",
        candidate_content="The release checklist is in the release docs.",
    )
    similarity = FixedSimilarityProvider(0.94)
    detector = MemoryDuplicateConflictDetector(
        review_repository=review_repository,
        memory_service=memory_service,
        similarity_provider=similarity,
        semantic_duplicate_threshold=0.9,
    )

    summary = detector.process_pending(limit=10)

    updated = review_repository.review_items[review_item.id]
    assert summary == {"selected": 1, "duplicates": 1, "conflicts": 0, "unchanged": 0}
    assert updated.review_kind == "duplicate"
    assert updated.reason == "semantic_duplicate"
    assert updated.candidate_payload["duplicate_memory_id"] == existing["id"]
    assert updated.candidate_payload["duplicate_score"] == 0.94


def test_detector_marks_contradiction_review_when_no_duplicate_matches():
    from team_cloud.memory.detectors import MemoryDuplicateConflictDetector

    memory_service, review_repository = _services()
    existing, _candidate, review_item = _seed_review(
        memory_service,
        review_repository,
        existing_content="Production deploys happen on Fridays.",
        candidate_content="Production deploys never happen on Fridays.",
    )
    contradiction = FixedContradictionProvider("conflicts with deploy calendar")
    detector = MemoryDuplicateConflictDetector(
        review_repository=review_repository,
        memory_service=memory_service,
        similarity_provider=FixedSimilarityProvider(0.2),
        contradiction_provider=contradiction,
    )

    summary = detector.process_pending(limit=10)

    updated = review_repository.review_items[review_item.id]
    assert summary == {"selected": 1, "duplicates": 0, "conflicts": 1, "unchanged": 0}
    assert updated.review_kind == "conflict"
    assert updated.reason == "contradiction"
    assert updated.candidate_payload["conflict_memory_id"] == existing["id"]
    assert updated.candidate_payload["conflict_reason"] == "conflicts with deploy calendar"
