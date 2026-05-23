from __future__ import annotations

import json


class FakeCasdoorDirectoryClient:
    def list_organizations(self):
        return [
            {
                "name": "hermes-labs",
                "displayName": "Hermes Labs",
                "status": "active",
            }
        ]

    def list_groups(self):
        return [
            {
                "owner": "hermes-labs",
                "name": "platform",
                "displayName": "Platform",
            }
        ]

    def list_users(self):
        return [
            {
                "id": "alice-id",
                "owner": "hermes-labs",
                "name": "alice",
                "displayName": "Alice",
                "email": "alice@example.com",
                "groups": ["platform"],
            },
            {
                "id": "bob-id",
                "owner": "hermes-labs",
                "name": "bob",
                "displayName": "Bob",
                "email": "bob@example.com",
                "groups": ["platform"],
                "isForbidden": True,
            },
        ]


def test_lazy_upsert_from_claims_creates_user_member_and_external_identity():
    from team_cloud.sync.casdoor import (
        CasdoorSyncWorker,
        InMemoryCasdoorSyncRepository,
    )

    repository = InMemoryCasdoorSyncRepository()
    worker = CasdoorSyncWorker(repository=repository)

    result = worker.lazy_upsert_from_claims(
        {
            "sub": "casdoor-user-1",
            "email": "admin@example.com",
            "name": "Admin",
            "organization": "hermes-labs",
            "groups": ["platform"],
            "roles": ["admin"],
            "access_token": "super-secret-token",
            "refresh_token": "super-secret-refresh-token",
        }
    )

    assert repository.users["casdoor-user-1"]["primary_email"] == "admin@example.com"
    assert repository.organizations["hermes-labs"]["name"] == "hermes-labs"
    assert repository.members[("hermes-labs", "casdoor-user-1")]["status"] == "active"
    assert repository.external_identities[
        ("casdoor", "casdoor-user-1", "hermes-labs")
    ]["status"] == "active"
    assert repository.team_memberships == {("hermes-labs", "platform", "casdoor-user-1")}
    assert repository.audit_events[-1]["action"] == "casdoor.lazy_upsert"
    assert result.counts["users"] == 1
    assert result.counts["members"] == 1

    serialized = json.dumps(result.to_dict()) + json.dumps(
        list(repository.external_identities.values()),
        sort_keys=True,
    )
    assert "super-secret-token" not in serialized
    assert "super-secret-refresh-token" not in serialized


def test_reconcile_syncs_casdoor_orgs_groups_and_users():
    from team_cloud.sync.casdoor import (
        CasdoorSyncWorker,
        InMemoryCasdoorSyncRepository,
    )

    repository = InMemoryCasdoorSyncRepository()
    worker = CasdoorSyncWorker(
        casdoor_client=FakeCasdoorDirectoryClient(),
        repository=repository,
    )

    result = worker.reconcile()

    assert result.counts["organizations"] == 1
    assert result.counts["teams"] == 1
    assert result.counts["users"] == 2
    assert repository.organizations["hermes-labs"]["name"] == "Hermes Labs"
    assert repository.teams[("hermes-labs", "platform")]["name"] == "Platform"
    assert repository.members[("hermes-labs", "alice-id")]["status"] == "active"
    assert repository.members[("hermes-labs", "bob-id")]["status"] == "suspended"
    assert any(
        event["action"] == "casdoor.reconcile"
        for event in repository.audit_events
    )


def test_disabled_user_propagation_suspends_member_and_emits_cleanup_intents():
    from team_cloud.sync.casdoor import (
        CasdoorSyncWorker,
        InMemoryCasdoorSyncRepository,
    )

    repository = InMemoryCasdoorSyncRepository()
    worker = CasdoorSyncWorker(repository=repository)

    result = worker.sync_user(
        {
            "id": "disabled-id",
            "owner": "hermes-labs",
            "name": "disabled",
            "displayName": "Disabled User",
            "email": "disabled@example.com",
            "groups": ["platform"],
            "isForbidden": True,
        }
    )

    assert repository.members[("hermes-labs", "disabled-id")]["status"] == "suspended"
    assert repository.revoked_sessions == [
        {"org_slug": "hermes-labs", "subject": "disabled-id"}
    ]
    assert repository.pending_pat_revocations == [
        {"org_slug": "hermes-labs", "subject": "disabled-id"}
    ]
    assert repository.spicedb_outbox[-1]["operation"] == "delete"
    assert repository.spicedb_outbox[-1]["relationships"] == [
        "organization:hermes-labs#member@user:disabled-id",
        "team:hermes-labs/platform#member@user:disabled-id",
    ]
    assert repository.audit_events[-1]["action"] == "casdoor.user_disabled"
    assert "propagate_disabled_user" in [command.action for command in result.commands]


def test_team_cloud_worker_runs_casdoor_reconcile(team_cloud_config):
    from team_cloud.sync.casdoor import (
        CasdoorSyncWorker,
        InMemoryCasdoorSyncRepository,
    )
    from team_cloud.worker import TeamCloudWorker

    repository = InMemoryCasdoorSyncRepository()
    sync_worker = CasdoorSyncWorker(
        casdoor_client=FakeCasdoorDirectoryClient(),
        repository=repository,
    )
    worker = TeamCloudWorker(
        team_cloud_config,
        queues=("casdoor_sync",),
        casdoor_sync_worker=sync_worker,
    )

    result = worker.run_casdoor_reconcile()

    assert result.counts["users"] == 2
    assert repository.members[("hermes-labs", "bob-id")]["status"] == "suspended"
    assert worker.heartbeat()["queues"] == ["casdoor_sync"]
