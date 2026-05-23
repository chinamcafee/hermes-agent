from __future__ import annotations

from datetime import UTC, datetime


NOW = datetime(2026, 5, 22, 14, 0, tzinfo=UTC)


def test_hard_delete_worker_cleans_member_rows_relationships_objects_and_audit():
    from team_cloud.admin.organizations import InMemoryOrganizationService
    from team_cloud.audit import InMemoryAuditLog
    from team_cloud.authz.outbox import InMemoryRelationshipOutboxRepository
    from team_cloud.cloud_sessions import InMemoryCloudSessionRepository
    from team_cloud.deletion import DataDeletionRequestService
    from team_cloud.deletion_worker import HardDeleteWorker
    from team_cloud.memory.service import InMemoryMemoryService
    from team_cloud.storage.minio import InMemoryObjectStore, ObjectManifestService

    audit_log = InMemoryAuditLog()
    outbox_repository = InMemoryRelationshipOutboxRepository()
    org_service = InMemoryOrganizationService(outbox_repository=outbox_repository)
    org_service.create_organization(slug="org-1", name="Hermes Labs")
    member = org_service.invite_member(
        org_id="org-1",
        email="alice@example.com",
        display_name="Alice",
        user_id="alice",
    )
    other_member = org_service.invite_member(
        org_id="org-1",
        email="bob@example.com",
        display_name="Bob",
        user_id="bob",
    )

    memory_service = InMemoryMemoryService()
    member_memory = memory_service.create_memory(
        {
            "org_id": "org-1",
            "scope": "personal",
            "subject_member_id": member["id"],
            "content": "Alice private memory",
        }
    )
    other_memory = memory_service.create_memory(
        {
            "org_id": "org-1",
            "scope": "personal",
            "subject_member_id": other_member["id"],
            "content": "Bob private memory",
        }
    )

    sessions = InMemoryCloudSessionRepository()
    member_session = sessions.create_session(
        org_id="org-1",
        team_id="team-1",
        project_id="project-1",
        owner_member_id=member["id"],
        title="Alice session",
    )
    other_session = sessions.create_session(
        org_id="org-1",
        team_id="team-1",
        project_id="project-1",
        owner_member_id=other_member["id"],
        title="Bob session",
    )

    object_store = InMemoryObjectStore()
    manifests = ObjectManifestService(object_store=object_store)
    member_object = manifests.upload_object(
        object_type="personal_backup",
        org_id="org-1",
        owner_member_id=member["id"],
        object_id="backup-alice-1",
        content=b"alice backup",
        content_type="application/zip",
        created_at=NOW,
    )
    other_object = manifests.upload_object(
        object_type="personal_backup",
        org_id="org-1",
        owner_member_id=other_member["id"],
        object_id="backup-bob-1",
        content=b"bob backup",
        content_type="application/zip",
        created_at=NOW,
    )

    deletion_service = DataDeletionRequestService(
        audit_log=audit_log,
        now=lambda: NOW,
        request_id_factory=lambda: "delete-request-1",
    )
    deletion_service.create_request(
        org_id="org-1",
        requester_member_id="owner-1",
        target_type="member",
        target_id=member["id"],
        mode="hard_delete",
    )
    deletion_service.approve_request(
        "delete-request-1",
        approver_member_id="security-1",
        scheduled_at=NOW,
    )
    deletion_service.run_due_requests(at=NOW)

    worker = HardDeleteWorker(
        deletion_service=deletion_service,
        audit_log=audit_log,
        org_service=org_service,
        memory_service=memory_service,
        cloud_session_repository=sessions,
        object_manifest_service=manifests,
        relationship_outbox_repository=outbox_repository,
        relationship_snapshot=lambda request: (
            f"organization:{request['org_id']}#member@user:alice",
        ),
        now=lambda: NOW,
    )

    summary = worker.process_ready(limit=10)

    assert summary == {"processed": 1, "completed": 1, "failed": 0, "dead_letter": 0}
    assert deletion_service.requests["delete-request-1"]["status"] == "completed"
    assert deletion_service.requests["delete-request-1"]["completed_at"] == "2026-05-22T14:00:00Z"
    assert ("org-1", member["id"]) not in org_service.members
    assert ("org-1", other_member["id"]) in org_service.members
    assert member_memory["id"] not in memory_service.items
    assert other_memory["id"] in memory_service.items
    assert member_session["id"] not in sessions._sessions
    assert other_session["id"] in sessions._sessions
    assert manifests.manifests[member_object["object_id"]]["status"] == "deleted"
    assert manifests.manifests[other_object["object_id"]]["status"] == "active"
    assert (member_object["bucket"], member_object["object_key"]) not in object_store.objects
    assert (other_object["bucket"], other_object["object_key"]) in object_store.objects
    assert any(
        item.operation == "delete"
        and item.relationships == ("organization:org-1#member@user:alice",)
        for item in outbox_repository.items.values()
    )
    assert audit_log.events[-1]["action"] == "data_deletion.completed"
    assert audit_log.events[-1]["metadata"]["target_id"] == member["id"]


def test_hard_delete_worker_retries_failures_and_dead_letters_without_completion():
    from team_cloud.audit import InMemoryAuditLog
    from team_cloud.deletion import DataDeletionRequestService
    from team_cloud.deletion_worker import HardDeleteWorker

    class FailingObjectManifestService:
        def __init__(self) -> None:
            self.manifests = {
                "backup-alice-1": {
                    "object_id": "backup-alice-1",
                    "org_id": "org-1",
                    "owner_member_id": "member-1",
                    "project_id": None,
                    "status": "active",
                }
            }

        def mark_deleted(self, object_id: str, *, deleted_at=None):
            raise RuntimeError(f"minio unavailable for {object_id}")

    audit_log = InMemoryAuditLog()
    deletion_service = DataDeletionRequestService(
        audit_log=audit_log,
        now=lambda: NOW,
        request_id_factory=lambda: "delete-request-2",
    )
    deletion_service.create_request(
        org_id="org-1",
        requester_member_id="owner-1",
        target_type="member",
        target_id="member-1",
        mode="hard_delete",
    )
    deletion_service.approve_request(
        "delete-request-2",
        approver_member_id="security-1",
        scheduled_at=NOW,
    )
    deletion_service.run_due_requests(at=NOW)
    worker = HardDeleteWorker(
        deletion_service=deletion_service,
        audit_log=audit_log,
        object_manifest_service=FailingObjectManifestService(),
        max_attempts=2,
        now=lambda: NOW,
    )

    first = worker.process_ready()
    second = worker.process_ready()
    request = deletion_service.requests["delete-request-2"]

    assert first == {"processed": 1, "completed": 0, "failed": 1, "dead_letter": 0}
    assert second == {"processed": 1, "completed": 0, "failed": 0, "dead_letter": 1}
    assert request["status"] == "dead_letter"
    assert request["worker_attempts"] == 2
    assert "minio unavailable" in request["last_error"]
    assert request["completed_at"] is None
    assert [event["action"] for event in audit_log.events][-2:] == [
        "data_deletion.worker_failed",
        "data_deletion.worker_dead_letter",
    ]
