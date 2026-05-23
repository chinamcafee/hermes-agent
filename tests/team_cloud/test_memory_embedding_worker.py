from __future__ import annotations


class DeterministicEmbeddingProvider:
    def __init__(self, *, fail: bool = False):
        self.fail = fail
        self.calls: list[list[str]] = []

    def embed_many(self, texts):
        self.calls.append(list(texts))
        if self.fail:
            raise RuntimeError("embedding provider unavailable")
        return tuple(
            (
                float(len(text)),
                float(sum(ord(char) for char in text) % 17),
                1.0,
            )
            for text in texts
        )


def test_embedding_worker_batches_pending_memory_and_records_model_version():
    from team_cloud.memory.embedding import (
        InMemoryMemoryEmbeddingRepository,
        MemoryEmbeddingWorker,
    )
    from team_cloud.memory.service import InMemoryMemoryService

    memory_service = InMemoryMemoryService()
    personal = memory_service.create_memory(
        {
            "org_id": "org-1",
            "scope": "personal",
            "subject_member_id": "alice",
            "content": "Alice prefers deterministic tests.",
        }
    )
    team = memory_service.create_memory(
        {
            "org_id": "org-1",
            "scope": "team_shared",
            "team_id": "team-1",
            "content": "Team release checklist.",
        }
    )
    deleted = memory_service.create_memory(
        {
            "org_id": "org-1",
            "scope": "personal",
            "subject_member_id": "bob",
            "content": "Deleted memory should not embed.",
        }
    )
    memory_service.delete_memory(deleted["id"])
    repository = InMemoryMemoryEmbeddingRepository(memory_service=memory_service)
    provider = DeterministicEmbeddingProvider()
    worker = MemoryEmbeddingWorker(
        repository=repository,
        embedding_provider=provider,
        embedding_model="text-embedding-3-small:v1",
        batch_size=2,
    )

    summary = worker.process_pending(limit=10)

    assert summary == {"selected": 2, "embedded": 2, "failed": 0, "skipped": 0}
    assert provider.calls == [
        [
            personal["normalized_content"],
            team["normalized_content"],
        ]
    ]
    personal_embedding = repository.get_embedding(
        memory_id=personal["id"],
        embedding_model="text-embedding-3-small:v1",
    )
    assert personal_embedding is not None
    assert personal_embedding.embedding_dim == 3
    assert personal_embedding.checksum_sha256 == personal["checksum_sha256"]
    assert repository.get_embedding(
        memory_id=deleted["id"],
        embedding_model="text-embedding-3-small:v1",
    ) is None


def test_embedding_worker_retries_failures_and_skips_dead_attempts():
    from team_cloud.memory.embedding import (
        InMemoryMemoryEmbeddingRepository,
        MemoryEmbeddingWorker,
    )
    from team_cloud.memory.service import InMemoryMemoryService

    memory_service = InMemoryMemoryService()
    memory = memory_service.create_memory(
        {
            "org_id": "org-1",
            "scope": "personal",
            "subject_member_id": "alice",
            "content": "Needs embedding retry.",
        }
    )
    repository = InMemoryMemoryEmbeddingRepository(memory_service=memory_service)
    failing_worker = MemoryEmbeddingWorker(
        repository=repository,
        embedding_provider=DeterministicEmbeddingProvider(fail=True),
        embedding_model="model:v1",
        max_attempts=2,
    )

    first = failing_worker.process_pending(limit=10)
    second = failing_worker.process_pending(limit=10)
    third = failing_worker.process_pending(limit=10)

    failure = repository.get_failure(
        memory_id=memory["id"],
        embedding_model="model:v1",
    )
    assert first == {"selected": 1, "embedded": 0, "failed": 1, "skipped": 0}
    assert second == {"selected": 1, "embedded": 0, "failed": 1, "skipped": 0}
    assert third == {"selected": 1, "embedded": 0, "failed": 0, "skipped": 1}
    assert failure is not None
    assert failure.attempts == 2
    assert failure.last_error == "embedding provider unavailable"
    assert repository.get_embedding(memory_id=memory["id"], embedding_model="model:v1") is None


def test_embedding_worker_backfills_changed_content_and_new_model_versions():
    from team_cloud.memory.embedding import (
        InMemoryMemoryEmbeddingRepository,
        MemoryEmbeddingWorker,
    )
    from team_cloud.memory.service import InMemoryMemoryService

    memory_service = InMemoryMemoryService()
    memory = memory_service.create_memory(
        {
            "org_id": "org-1",
            "scope": "personal",
            "subject_member_id": "alice",
            "content": "Original content.",
        }
    )
    repository = InMemoryMemoryEmbeddingRepository(memory_service=memory_service)
    provider = DeterministicEmbeddingProvider()
    worker_v1 = MemoryEmbeddingWorker(
        repository=repository,
        embedding_provider=provider,
        embedding_model="model:v1",
    )

    assert worker_v1.process_pending(limit=10)["embedded"] == 1
    assert worker_v1.process_pending(limit=10)["selected"] == 0

    updated = memory_service.update_memory(
        memory["id"],
        {"content": "Updated content.", "actor_member_id": "alice"},
    )
    assert worker_v1.process_pending(limit=10)["embedded"] == 1
    v1_embedding = repository.get_embedding(
        memory_id=memory["id"],
        embedding_model="model:v1",
    )
    assert v1_embedding is not None
    assert v1_embedding.checksum_sha256 == updated["checksum_sha256"]

    worker_v2 = MemoryEmbeddingWorker(
        repository=repository,
        embedding_provider=provider,
        embedding_model="model:v2",
    )
    assert worker_v2.process_pending(limit=10)["embedded"] == 1
    assert repository.get_embedding(
        memory_id=memory["id"],
        embedding_model="model:v2",
    ) is not None
