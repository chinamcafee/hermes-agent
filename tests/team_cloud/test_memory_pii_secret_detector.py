from __future__ import annotations


class FixedSafetyClassifier:
    def __init__(self, *, sensitivity: str, findings: list[str], reject: bool = False):
        self.sensitivity = sensitivity
        self.findings = findings
        self.reject = reject
        self.calls = []

    def classify(self, text: str):
        from team_cloud.memory.safety import SafetyDetection

        self.calls.append(text)
        return SafetyDetection(
            sensitivity=self.sensitivity,
            findings=tuple(self.findings),
            reject=self.reject,
        )


def _seed_review_item(*, content: str):
    from team_cloud.memory.extraction import InMemoryMemoryObservationRepository
    from team_cloud.memory.service import InMemoryMemoryService

    memory_service = InMemoryMemoryService()
    review_repository = InMemoryMemoryObservationRepository()
    memory = memory_service.create_memory(
        {
            "org_id": "org-1",
            "scope": "team_shared",
            "team_id": "team-1",
            "content": content,
        }
    )
    review_item = review_repository.create_review_item(
        org_id="org-1",
        memory_id=memory["id"],
        proposed_scope="team_shared",
        reviewer_member_id=None,
        review_kind="team_candidate",
        candidate_payload={"content": content},
        confidence=0.8,
    )
    return memory_service, review_repository, memory, review_item


def test_pii_detector_marks_review_item_and_memory_sensitivity():
    from team_cloud.memory.safety import MemoryPiiSecretDetector

    memory_service, review_repository, memory, review_item = _seed_review_item(
        content="Alice email is alice@example.com.",
    )
    detector = MemoryPiiSecretDetector(
        review_repository=review_repository,
        memory_service=memory_service,
        classifier=FixedSafetyClassifier(
            sensitivity="pii",
            findings=["email_address"],
        ),
    )

    summary = detector.process_pending(limit=10)

    updated_review = review_repository.review_items[review_item.id]
    updated_memory = memory_service.items[memory["id"]]
    assert summary == {"selected": 1, "pii": 1, "secrets": 0, "rejected": 0, "unchanged": 0}
    assert updated_review.review_kind == "pii"
    assert updated_review.reason == "pii_detected"
    assert updated_review.status == "pending"
    assert updated_review.candidate_payload["safety_findings"] == ["email_address"]
    assert updated_memory["sensitivity"] == "pii"
    assert updated_memory["status"] == "pending_review"


def test_secret_detector_rejects_secret_candidate():
    from team_cloud.memory.safety import MemoryPiiSecretDetector

    memory_service, review_repository, memory, review_item = _seed_review_item(
        content="OPENAI_API_KEY=sk-live-secret",
    )
    detector = MemoryPiiSecretDetector(
        review_repository=review_repository,
        memory_service=memory_service,
        classifier=FixedSafetyClassifier(
            sensitivity="secret",
            findings=["api_key"],
            reject=True,
        ),
    )

    summary = detector.process_pending(limit=10)

    updated_review = review_repository.review_items[review_item.id]
    updated_memory = memory_service.items[memory["id"]]
    assert summary == {"selected": 1, "pii": 0, "secrets": 1, "rejected": 1, "unchanged": 0}
    assert updated_review.review_kind == "pii"
    assert updated_review.status == "rejected"
    assert updated_review.reason == "secret_detected"
    assert updated_review.candidate_payload["safety_findings"] == ["api_key"]
    assert updated_memory["sensitivity"] == "secret"
    assert updated_memory["status"] == "rejected"


def test_pii_detector_leaves_normal_candidate_unchanged():
    from team_cloud.memory.safety import MemoryPiiSecretDetector

    memory_service, review_repository, memory, review_item = _seed_review_item(
        content="Release checklist lives in docs/releases.md.",
    )
    detector = MemoryPiiSecretDetector(
        review_repository=review_repository,
        memory_service=memory_service,
        classifier=FixedSafetyClassifier(
            sensitivity="normal",
            findings=[],
        ),
    )

    summary = detector.process_pending(limit=10)

    updated_review = review_repository.review_items[review_item.id]
    updated_memory = memory_service.items[memory["id"]]
    assert summary == {"selected": 1, "pii": 0, "secrets": 0, "rejected": 0, "unchanged": 1}
    assert updated_review == review_item
    assert updated_memory["sensitivity"] == "normal"
    assert updated_memory["status"] == "pending_review"
