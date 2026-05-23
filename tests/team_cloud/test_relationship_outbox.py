from __future__ import annotations


class FakeRelationshipWriter:
    def __init__(self, *, fail: bool = False):
        self.fail = fail
        self.calls = []

    def write_relationships(self, *, relationships, operation):
        self.calls.append({"relationships": relationships, "operation": operation})
        if self.fail:
            raise RuntimeError("spicedb write failed")
        return {"written": len(relationships), "operation": operation}


def test_enqueue_relationship_outbox_is_idempotent_and_serializes_relationships():
    from team_cloud.authz.outbox import (
        InMemoryRelationshipOutboxRepository,
        RelationshipOutboxService,
    )
    from team_cloud.authz.spicedb import Relationship, ResourceRef, SubjectRef

    repository = InMemoryRelationshipOutboxRepository()
    service = RelationshipOutboxService(repository)
    relationship = Relationship(
        resource=ResourceRef("organization", "org-1"),
        relation="member",
        subject=SubjectRef("user", "alice"),
    )

    first = service.enqueue(
        org_id="org-1",
        aggregate_type="member",
        aggregate_id="member-1",
        operation="touch",
        relationships=[relationship],
    )
    second = service.enqueue(
        org_id="org-1",
        aggregate_type="member",
        aggregate_id="member-1",
        operation="touch",
        relationships=[relationship],
    )

    assert first.id == second.id
    assert len(repository.items) == 1
    assert first.relationships == ("organization:org-1#member@user:alice",)
    assert first.idempotency_key == second.idempotency_key
    assert first.status == "pending"


def test_worker_applies_pending_items_to_spicedb_and_marks_applied():
    from team_cloud.authz.outbox import (
        InMemoryRelationshipOutboxRepository,
        RelationshipOutboxService,
        RelationshipOutboxWorker,
    )

    repository = InMemoryRelationshipOutboxRepository()
    service = RelationshipOutboxService(repository)
    item = service.enqueue(
        org_id="org-1",
        aggregate_type="member",
        aggregate_id="member-1",
        operation="delete",
        relationships=["organization:org-1#member@user:alice"],
    )
    writer = FakeRelationshipWriter()
    worker = RelationshipOutboxWorker(repository=repository, relationship_writer=writer)

    summary = worker.process_pending(limit=10)

    assert summary == {"processed": 1, "applied": 1, "failed": 0, "dead_letter": 0}
    assert writer.calls == [
        {
            "relationships": ["organization:org-1#member@user:alice"],
            "operation": "delete",
        }
    ]
    assert repository.items[item.id].status == "applied"
    assert repository.items[item.id].processed_at is not None


def test_worker_retries_failures_and_dead_letters_after_threshold():
    from team_cloud.authz.outbox import (
        InMemoryRelationshipOutboxRepository,
        RelationshipOutboxService,
        RelationshipOutboxWorker,
    )

    repository = InMemoryRelationshipOutboxRepository()
    service = RelationshipOutboxService(repository)
    item = service.enqueue(
        org_id="org-1",
        aggregate_type="member",
        aggregate_id="member-1",
        operation="touch",
        relationships=["organization:org-1#member@user:alice"],
    )
    worker = RelationshipOutboxWorker(
        repository=repository,
        relationship_writer=FakeRelationshipWriter(fail=True),
        max_attempts=2,
    )

    first = worker.process_pending(limit=10)
    second = worker.process_pending(limit=10)

    assert first == {"processed": 1, "applied": 0, "failed": 1, "dead_letter": 0}
    assert second == {"processed": 1, "applied": 0, "failed": 0, "dead_letter": 1}
    failed_item = repository.items[item.id]
    assert failed_item.status == "dead_letter"
    assert failed_item.attempts == 2
    assert failed_item.last_error == "spicedb write failed"


def test_resources_fail_closed_until_relationship_outbox_is_applied():
    from team_cloud.authz.outbox import (
        InMemoryRelationshipOutboxRepository,
        RelationshipOutboxService,
    )

    repository = InMemoryRelationshipOutboxRepository()
    service = RelationshipOutboxService(repository)
    item = service.enqueue(
        org_id="org-1",
        aggregate_type="project",
        aggregate_id="project-1",
        operation="touch",
        relationships=["project:project-1#member@user:alice"],
    )

    assert service.requires_fail_closed(
        aggregate_type="project",
        aggregate_id="project-1",
    )

    repository.mark_applied(item.id)

    assert not service.requires_fail_closed(
        aggregate_type="project",
        aggregate_id="project-1",
    )
