from __future__ import annotations


class StaticExtractor:
    def __init__(self, candidates=(), *, fail: bool = False):
        self.candidates = tuple(candidates)
        self.fail = fail
        self.calls = []

    def extract(self, observation):
        self.calls.append(observation.id)
        if self.fail:
            raise RuntimeError("extractor unavailable")
        return self.candidates


def test_extraction_worker_writes_personal_memory_and_team_review_items():
    from team_cloud.memory.extraction import (
        InMemoryMemoryObservationRepository,
        MemoryExtractionCandidate,
        MemoryExtractionWorker,
    )
    from team_cloud.memory.service import InMemoryMemoryService

    repository = InMemoryMemoryObservationRepository()
    memory_service = InMemoryMemoryService()
    observation = repository.create_observation(
        org_id="org-1",
        session_id="session-1",
        member_id="alice",
        team_id="team-1",
        project_id="project-1",
        observation={"messages": [{"role": "user", "content": "remember this"}]},
    )
    extractor = StaticExtractor(
        [
            MemoryExtractionCandidate(
                scope="personal",
                content="Alice prefers deterministic tests.",
                memory_type="preference",
                confidence=0.91,
            ),
            MemoryExtractionCandidate(
                scope="team_shared",
                content="Release checklist lives in docs/releases.md.",
                memory_type="procedure",
                confidence=0.84,
                review_kind="team_candidate",
            ),
        ]
    )
    worker = MemoryExtractionWorker(
        observation_repository=repository,
        memory_service=memory_service,
        extractor=extractor,
    )

    summary = worker.process_pending(limit=10)

    assert summary == {
        "selected": 1,
        "created_memories": 2,
        "review_items": 1,
        "ignored": 0,
        "failed": 0,
    }
    assert extractor.calls == [observation.id]
    memories = list(memory_service.items.values())
    assert memories[0]["scope"] == "personal"
    assert memories[0]["subject_member_id"] == "alice"
    assert memories[0]["status"] == "active"
    assert memories[0]["source_ref"] == {"observation_id": observation.id}
    assert memories[1]["scope"] == "team_shared"
    assert memories[1]["team_id"] == "team-1"
    assert memories[1]["project_id"] == "project-1"
    assert memories[1]["status"] == "pending_review"
    review_item = next(iter(repository.review_items.values()))
    assert review_item.memory_id == memories[1]["id"]
    assert review_item.proposed_scope == "team_shared"
    assert review_item.review_kind == "team_candidate"
    assert review_item.confidence == 0.84
    assert review_item.candidate_payload["content"] == memories[1]["content"]
    updated_observation = repository.observations[observation.id]
    assert updated_observation.status == "extracted"
    assert updated_observation.confidence == 0.875
    assert updated_observation.extraction_trace["candidate_count"] == 2
    assert updated_observation.extraction_trace["created_memory_ids"] == [
        memories[0]["id"],
        memories[1]["id"],
    ]
    assert updated_observation.processed_at is not None


def test_extraction_worker_marks_observation_ignored_when_no_candidates():
    from team_cloud.memory.extraction import (
        InMemoryMemoryObservationRepository,
        MemoryExtractionWorker,
    )
    from team_cloud.memory.service import InMemoryMemoryService

    repository = InMemoryMemoryObservationRepository()
    observation = repository.create_observation(
        org_id="org-1",
        session_id="session-1",
        member_id="alice",
        team_id="team-1",
        observation={"messages": []},
    )
    worker = MemoryExtractionWorker(
        observation_repository=repository,
        memory_service=InMemoryMemoryService(),
        extractor=StaticExtractor([]),
    )

    summary = worker.process_pending(limit=10)

    assert summary == {
        "selected": 1,
        "created_memories": 0,
        "review_items": 0,
        "ignored": 1,
        "failed": 0,
    }
    updated_observation = repository.observations[observation.id]
    assert updated_observation.status == "ignored"
    assert updated_observation.extraction_trace == {"candidate_count": 0}


def test_extraction_worker_marks_observation_error_when_extractor_fails():
    from team_cloud.memory.extraction import (
        InMemoryMemoryObservationRepository,
        MemoryExtractionWorker,
    )
    from team_cloud.memory.service import InMemoryMemoryService

    repository = InMemoryMemoryObservationRepository()
    observation = repository.create_observation(
        org_id="org-1",
        session_id="session-1",
        member_id="alice",
        team_id="team-1",
        observation={"messages": [{"role": "assistant", "content": "ok"}]},
    )
    worker = MemoryExtractionWorker(
        observation_repository=repository,
        memory_service=InMemoryMemoryService(),
        extractor=StaticExtractor(fail=True),
    )

    summary = worker.process_pending(limit=10)

    assert summary == {
        "selected": 1,
        "created_memories": 0,
        "review_items": 0,
        "ignored": 0,
        "failed": 1,
    }
    updated_observation = repository.observations[observation.id]
    assert updated_observation.status == "error"
    assert updated_observation.error == "extractor unavailable"
