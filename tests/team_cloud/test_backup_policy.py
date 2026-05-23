from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient


NOW = datetime(2026, 5, 22, 12, 0, tzinfo=UTC)


def test_backup_policy_service_defaults_upserts_and_finds_due_policies():
    from team_cloud.backup.policy import BackupPolicyService

    service = BackupPolicyService(now=lambda: NOW)

    default = service.get_policy(org_id="org-1", member_id="alice")
    saved = service.upsert_policy(
        org_id="org-1",
        member_id="alice",
        cadence="daily",
        enabled=True,
        retention_count=7,
        include_deleted=True,
        include_embeddings=False,
        encryption_mode="user_passphrase",
        notification_channels=["email", "in_app"],
        next_run_at=NOW,
    )

    assert default["enabled"] is False
    assert default["cadence"] == "weekly"
    assert default["retention_count"] == 8
    assert saved["id"] == "backup-policy-1"
    assert saved["include_deleted"] is True
    assert saved["encryption_mode"] == "user_passphrase"
    assert service.due_policies(at=NOW) == [saved]


def test_backup_policy_service_rejects_invalid_values():
    import pytest

    from team_cloud.backup.policy import BackupPolicyService

    service = BackupPolicyService(now=lambda: NOW)

    with pytest.raises(ValueError, match="invalid_cadence"):
        service.upsert_policy(org_id="org-1", member_id="alice", cadence="hourly")
    with pytest.raises(ValueError, match="invalid_retention_count"):
        service.upsert_policy(org_id="org-1", member_id="alice", retention_count=0)
    with pytest.raises(ValueError, match="invalid_encryption_mode"):
        service.upsert_policy(
            org_id="org-1",
            member_id="alice",
            encryption_mode="plaintext",
        )


def test_backup_policy_api_gets_and_updates_member_policy():
    from team_cloud.api import create_app
    from team_cloud.backup.policy import BackupPolicyService

    service = BackupPolicyService(now=lambda: NOW)
    client = TestClient(create_app(backup_policy_service=service, oidc_client=object()))

    default = client.get(
        "/v1/me/memory-backup-policy",
        params={"org_id": "org-1", "member_id": "alice"},
    )
    updated = client.put(
        "/v1/me/memory-backup-policy",
        json={
            "org_id": "org-1",
            "member_id": "alice",
            "cadence": "monthly",
            "enabled": True,
            "retention_count": 12,
            "include_deleted": False,
            "include_embeddings": True,
            "encryption_mode": "org_managed",
            "notification_channels": ["in_app"],
        },
    )

    assert default.status_code == 200
    assert default.json()["enabled"] is False
    assert updated.status_code == 200
    assert updated.json()["cadence"] == "monthly"
    assert updated.json()["enabled"] is True
    assert updated.json()["retention_count"] == 12
    assert updated.json()["include_embeddings"] is True


def test_backup_policy_api_rejects_invalid_payload():
    from team_cloud.api import create_app
    from team_cloud.backup.policy import BackupPolicyService

    client = TestClient(
        create_app(backup_policy_service=BackupPolicyService(), oidc_client=object())
    )

    response = client.put(
        "/v1/me/memory-backup-policy",
        json={
            "org_id": "org-1",
            "member_id": "alice",
            "cadence": "hourly",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "invalid_cadence"
