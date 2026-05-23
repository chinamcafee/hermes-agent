from __future__ import annotations

from datetime import UTC, datetime, timedelta


NOW = datetime(2026, 5, 22, 12, 0, tzinfo=UTC)


def test_deletion_request_lifecycle_records_audit_and_ready_worker_contract():
    from team_cloud.audit import InMemoryAuditLog
    from team_cloud.deletion import DataDeletionRequestService

    audit_log = InMemoryAuditLog()
    service = DataDeletionRequestService(
        audit_log=audit_log,
        now=lambda: NOW,
        request_id_factory=lambda: "delete-request-1",
    )

    request = service.create_request(
        org_id="org-1",
        requester_member_id="owner-1",
        target_type="member",
        target_id="member-2",
        mode="hard_delete",
        export_before_delete=True,
        export_id="org-export-1",
        reason="GDPR erasure",
    )
    approved = service.approve_request(
        "delete-request-1",
        approver_member_id="security-1",
        scheduled_at=NOW + timedelta(hours=1),
    )

    assert request["id"] == "delete-request-1"
    assert request["approval_status"] == "pending"
    assert request["status"] == "pending_approval"
    assert approved["approval_status"] == "approved"
    assert approved["status"] == "scheduled"
    assert service.due_requests(at=NOW) == []
    assert service.due_requests(at=NOW + timedelta(hours=1)) == [approved]

    ready = service.run_due_requests(at=NOW + timedelta(hours=1))

    assert ready == [service.requests["delete-request-1"]]
    assert ready[0]["status"] == "ready_for_worker"
    assert ready[0]["completed_at"] is None
    assert ready[0]["execution_plan"] == [
        "disable_access",
        "export_before_delete",
        "delete_relationships",
        "soft_delete_rows",
        "delete_objects",
        "hard_delete_rows_after_retention",
        "write_final_audit",
    ]
    assert [event["action"] for event in audit_log.events] == [
        "data_deletion.requested",
        "data_deletion.approved",
        "data_deletion.ready_for_worker",
    ]
    assert audit_log.events[-1]["metadata"]["target_type"] == "member"
    assert audit_log.events[-1]["metadata"]["export_id"] == "org-export-1"


def test_deletion_request_rejects_invalid_target_mode_and_unapproved_execution():
    import pytest

    from team_cloud.deletion import DataDeletionRequestService

    service = DataDeletionRequestService(now=lambda: NOW)

    with pytest.raises(ValueError, match="invalid_target_type"):
        service.create_request(
            org_id="org-1",
            requester_member_id="owner-1",
            target_type="document",
            target_id="doc-1",
            mode="hard_delete",
        )
    with pytest.raises(ValueError, match="invalid_deletion_mode"):
        service.create_request(
            org_id="org-1",
            requester_member_id="owner-1",
            target_type="member",
            target_id="member-2",
            mode="purge",
        )

    request = service.create_request(
        org_id="org-1",
        requester_member_id="owner-1",
        target_type="project",
        target_id="project-1",
        mode="soft_delete",
    )

    assert service.due_requests(at=NOW) == []
    assert service.run_due_requests(at=NOW) == []
    with pytest.raises(ValueError, match="request_not_approved"):
        service.mark_completed(request["id"], completed_by_member_id="worker-1")
