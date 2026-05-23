from __future__ import annotations

from datetime import UTC, datetime, timedelta


NOW = datetime(2026, 5, 22, 16, 0, tzinfo=UTC)


def test_break_glass_approval_access_and_expiry_are_audited_and_notified():
    from team_cloud.audit import InMemoryAuditLog
    from team_cloud.authz.outbox import InMemoryRelationshipOutboxRepository
    from team_cloud.break_glass import BreakGlassService

    audit_log = InMemoryAuditLog()
    outbox_repository = InMemoryRelationshipOutboxRepository()
    service = BreakGlassService(
        audit_log=audit_log,
        relationship_outbox_repository=outbox_repository,
        now=lambda: NOW,
        request_id_factory=lambda: "break-glass-1",
    )

    request = service.create_request(
        org_id="org-1",
        requester_member_id="owner-1",
        requester_role="owner",
        target_member_id="member-2",
        resource_type="memory",
        resource_id="memory-1",
        permission="break_glass_read_personal",
        reason="Incident response",
        ticket_id="INC-123",
        starts_at=NOW,
        expires_at=NOW + timedelta(hours=1),
    )
    approved = service.approve_request(
        "break-glass-1",
        approver_member_id="security-1",
        approver_role="security_admin",
    )
    access_event = service.record_access(
        "break-glass-1",
        actor_member_id="owner-1",
        at=NOW + timedelta(minutes=30),
    )
    expired = service.expire_requests(at=NOW + timedelta(hours=2))

    assert request["status"] == "pending_approval"
    assert request["required_approver_role"] == "security_admin"
    assert approved["status"] == "active"
    assert approved["approval_status"] == "approved"
    assert access_event["action"] == "break_glass.accessed"
    assert expired == [service.requests["break-glass-1"]]
    assert service.requests["break-glass-1"]["status"] == "expired"
    assert [
        (item.operation, item.relationships)
        for item in outbox_repository.items.values()
    ] == [
        ("create", ("memory:memory-1#approved_break_glass_reader@user:owner-1",)),
        ("delete", ("memory:memory-1#approved_break_glass_reader@user:owner-1",)),
    ]
    assert [event["action"] for event in audit_log.events] == [
        "break_glass.requested",
        "break_glass.approved",
        "break_glass.accessed",
        "break_glass.expired",
    ]
    assert service.notifications == [
        {
            "org_id": "org-1",
            "recipient_member_id": "member-2",
            "type": "break_glass_accessed",
            "request_id": "break-glass-1",
            "resource_type": "memory",
            "resource_id": "memory-1",
        }
    ]


def test_break_glass_enforces_two_person_roles_window_and_delayed_notification():
    import pytest

    from team_cloud.audit import InMemoryAuditLog
    from team_cloud.break_glass import BreakGlassService

    audit_log = InMemoryAuditLog()
    service = BreakGlassService(
        audit_log=audit_log,
        now=lambda: NOW,
        request_id_factory=lambda: "break-glass-2",
    )

    with pytest.raises(ValueError, match="invalid_break_glass_requester_role"):
        service.create_request(
            org_id="org-1",
            requester_member_id="admin-1",
            requester_role="admin",
            target_member_id="member-2",
            resource_type="backup",
            resource_id="backup-1",
            permission="break_glass_read",
            reason="Incident response",
            ticket_id="INC-124",
            starts_at=NOW,
            expires_at=NOW + timedelta(hours=1),
        )

    request = service.create_request(
        org_id="org-1",
        requester_member_id="security-1",
        requester_role="security_admin",
        target_member_id="member-2",
        resource_type="backup",
        resource_id="backup-1",
        permission="break_glass_read",
        reason="Legal hold investigation",
        ticket_id="INC-125",
        starts_at=NOW + timedelta(minutes=10),
        expires_at=NOW + timedelta(hours=1),
        delayed_notification=True,
    )

    with pytest.raises(ValueError, match="break_glass_requires_different_approver"):
        service.approve_request(
            request["id"],
            approver_member_id="security-1",
            approver_role="owner",
        )
    with pytest.raises(ValueError, match="invalid_break_glass_approver_role"):
        service.approve_request(
            request["id"],
            approver_member_id="owner-1",
            approver_role="security_admin",
        )

    approved = service.approve_request(
        request["id"],
        approver_member_id="owner-1",
        approver_role="owner",
    )

    assert approved["status"] == "scheduled"
    with pytest.raises(ValueError, match="break_glass_not_active"):
        service.record_access(
            request["id"],
            actor_member_id="security-1",
            at=NOW,
        )
    service.record_access(
        request["id"],
        actor_member_id="security-1",
        at=NOW + timedelta(minutes=15),
    )
    assert service.notifications == []
