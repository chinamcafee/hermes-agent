from __future__ import annotations

from datetime import UTC, datetime, timedelta
import hashlib

import pytest
from fastapi.testclient import TestClient


NOW = datetime(2026, 5, 22, 20, 0, tzinfo=UTC)


def test_notification_service_records_backup_failure_dedupes_and_acknowledges():
    from team_cloud.notifications import InMemoryNotificationService

    service = InMemoryNotificationService(now=lambda: NOW)

    first = service.notify_backup_failure(
        org_id="org-1",
        member_id="alice",
        backup_id="backup-1",
        policy_id="policy-1",
        error="checksum_mismatch",
        channels=("in_app", "email"),
    )
    second = service.notify_backup_failure(
        org_id="org-1",
        member_id="alice",
        backup_id="backup-1",
        policy_id="policy-1",
        error="checksum_mismatch",
        channels=("in_app", "email"),
    )

    assert second["id"] == first["id"]
    assert service.list_notifications(
        org_id="org-1",
        recipient_member_id="alice",
    ) == [first]
    assert first["type"] == "backup_failure"
    assert first["severity"] == "warning"
    assert first["channels"] == ["in_app", "email"]
    assert first["payload"]["backup_id"] == "backup-1"
    assert first["payload"]["error"] == "checksum_mismatch"

    acknowledged = service.acknowledge(first["id"], actor_member_id="alice")

    assert acknowledged["status"] == "acknowledged"
    assert acknowledged["acknowledged_by"] == "alice"
    assert acknowledged["acknowledged_at"] == "2026-05-22T20:00:00Z"


def test_backup_storage_emits_notification_on_upload_failure():
    from team_cloud.backup.exporter import BackupExportResult
    from team_cloud.backup.storage import PersonalBackupStorageService
    from team_cloud.notifications import InMemoryNotificationService
    from team_cloud.storage.minio import InMemoryObjectStore, ObjectManifestService

    notifications = InMemoryNotificationService(now=lambda: NOW)
    storage = PersonalBackupStorageService(
        manifest_service=ObjectManifestService(object_store=InMemoryObjectStore()),
        notification_service=notifications,
        now=lambda: NOW,
    )
    export = BackupExportResult(
        backup_id="backup-1",
        encrypted_bytes=b"encrypted backup bytes",
        manifest={
            "backup_id": "backup-1",
            "org_id": "org-1",
            "owner_member_id": "alice",
            "checksum_sha256": hashlib.sha256(b"different bytes").hexdigest(),
        },
    )

    with pytest.raises(ValueError, match="checksum_mismatch"):
        storage.upload_export(export, policy_id="policy-1")

    event = notifications.list_notifications(
        org_id="org-1",
        recipient_member_id="alice",
    )[0]
    failed_job = list(storage.jobs.values())[0]
    assert event["type"] == "backup_failure"
    assert event["payload"]["backup_id"] == "backup-1"
    assert event["payload"]["policy_id"] == "policy-1"
    assert event["payload"]["error"] == "checksum_mismatch"
    assert failed_job["status"] == "failed"
    assert failed_job["error"] == "checksum_mismatch"


def test_break_glass_access_uses_notification_service_and_respects_delay():
    from team_cloud.break_glass import BreakGlassService
    from team_cloud.notifications import InMemoryNotificationService

    notifications = InMemoryNotificationService(now=lambda: NOW)
    service = BreakGlassService(
        notification_service=notifications,
        now=lambda: NOW,
        request_id_factory=lambda: "break-glass-1",
    )
    request = service.create_request(
        org_id="org-1",
        requester_member_id="owner-1",
        requester_role="owner",
        target_member_id="alice",
        resource_type="backup",
        resource_id="backup-1",
        permission="break_glass_read",
        reason="incident response",
        ticket_id="SEC-1",
        starts_at=NOW - timedelta(minutes=1),
        expires_at=NOW + timedelta(minutes=10),
    )
    service.approve_request(
        request["id"],
        approver_member_id="sec-1",
        approver_role="security_admin",
    )

    service.record_access(request["id"], actor_member_id="owner-1")

    events = notifications.list_notifications(
        org_id="org-1",
        recipient_member_id="alice",
    )
    assert events[0]["type"] == "break_glass_accessed"
    assert events[0]["resource_type"] == "backup"
    assert events[0]["resource_id"] == "backup-1"
    assert events[0]["payload"]["request_id"] == "break-glass-1"

    delayed_service = BreakGlassService(
        notification_service=notifications,
        now=lambda: NOW,
        request_id_factory=lambda: "break-glass-2",
    )
    delayed = delayed_service.create_request(
        org_id="org-1",
        requester_member_id="sec-1",
        requester_role="security_admin",
        target_member_id="bob",
        resource_type="memory",
        resource_id="mem-1",
        permission="break_glass_read_personal",
        reason="legal hold",
        ticket_id="LEGAL-1",
        starts_at=NOW - timedelta(minutes=1),
        expires_at=NOW + timedelta(minutes=10),
        delayed_notification=True,
    )
    delayed_service.approve_request(
        delayed["id"],
        approver_member_id="owner-1",
        approver_role="owner",
    )
    delayed_service.record_access(delayed["id"], actor_member_id="sec-1")

    assert notifications.list_notifications(
        org_id="org-1",
        recipient_member_id="bob",
    ) == []


def test_review_service_emits_backlog_notification_when_threshold_is_met():
    from team_cloud.memory.extraction import InMemoryMemoryObservationRepository
    from team_cloud.memory.review import InMemoryMemoryReviewService
    from team_cloud.memory.service import InMemoryMemoryService
    from team_cloud.notifications import InMemoryNotificationService

    notifications = InMemoryNotificationService(now=lambda: NOW)
    memory_service = InMemoryMemoryService()
    review_repository = InMemoryMemoryObservationRepository()
    review_service = InMemoryMemoryReviewService(
        review_repository=review_repository,
        memory_service=memory_service,
        notification_service=notifications,
    )
    for index in range(3):
        memory = memory_service.create_memory(
            {
                "org_id": "org-1",
                "scope": "team_shared",
                "team_id": "team-1",
                "project_id": "project-1",
                "content": f"Draft memory {index}",
                "memory_type": "fact",
            }
        )
        review_repository.create_review_item(
            org_id="org-1",
            memory_id=memory["id"],
            proposed_scope="team_shared",
            reviewer_member_id=None,
            review_kind="team_candidate",
            candidate_payload={"content": memory["content"]},
            confidence=0.8,
        )

    skipped = review_service.notify_review_backlog(
        org_id="org-1",
        reviewer_member_ids=["reviewer-1"],
        threshold_count=4,
        review_kind="team_candidate",
    )
    event = review_service.notify_review_backlog(
        org_id="org-1",
        reviewer_member_ids=["reviewer-1"],
        threshold_count=2,
        review_kind="team_candidate",
    )

    assert skipped is None
    assert event["type"] == "review_backlog"
    assert event["recipient_member_ids"] == ["reviewer-1"]
    assert event["payload"]["pending_count"] == 3
    assert event["payload"]["review_kind"] == "team_candidate"


def test_notifications_api_lists_and_acknowledges_events():
    from team_cloud.api import create_app
    from team_cloud.notifications import InMemoryNotificationService

    notifications = InMemoryNotificationService(now=lambda: NOW)
    event = notifications.notify_break_glass_accessed(
        org_id="org-1",
        target_member_id="alice",
        request_id="break-glass-1",
        resource_type="backup",
        resource_id="backup-1",
        requester_member_id="owner-1",
    )
    client = TestClient(
        create_app(
            oidc_client=object(),
            notification_service=notifications,
        )
    )

    listed = client.get(
        "/api/notifications",
        params={"org_id": "org-1", "recipient_member_id": "alice"},
    )
    acknowledged = client.post(
        f"/api/notifications/{event['id']}/ack",
        json={"actor_member_id": "alice"},
    )

    assert listed.status_code == 200
    assert listed.json()["items"][0]["id"] == event["id"]
    assert acknowledged.status_code == 200
    assert acknowledged.json()["status"] == "acknowledged"
