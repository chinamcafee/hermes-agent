from __future__ import annotations

import pytest


class FakeSpiceDBTransport:
    def __init__(self, *, fail: bool = False):
        self.fail = fail
        self.check_calls = []
        self.lookup_calls = []
        self.write_calls = []

    def check_permission(self, *, subject, resource, permission, consistency):
        self.check_calls.append(
            {
                "subject": subject,
                "resource": resource,
                "permission": permission,
                "consistency": consistency,
            }
        )
        if self.fail:
            raise RuntimeError("spicedb unavailable")
        return permission in {"read_personal", "terminal_execute", "run_agent"}

    def lookup_resources(self, *, subject, resource_type, permission, consistency):
        self.lookup_calls.append(
            {
                "subject": subject,
                "resource_type": resource_type,
                "permission": permission,
                "consistency": consistency,
            }
        )
        if self.fail:
            raise RuntimeError("spicedb unavailable")
        return [f"{resource_type}:allowed-1", f"{resource_type}:allowed-2"]

    def write_relationships(self, *, relationships, operation):
        self.write_calls.append(
            {
                "relationships": relationships,
                "operation": operation,
            }
        )
        if self.fail:
            raise RuntimeError("spicedb unavailable")
        return {"written": len(relationships), "operation": operation}


def test_product_permission_mapping_uses_schema_permission_names():
    from team_cloud.authz.spicedb import permission_for_action

    assert permission_for_action("memory.personal.read", "memory") == "read_personal"
    assert permission_for_action("memory.team.read", "memory") == "read_team"
    assert permission_for_action("tool.terminal.execute", "tool") == "terminal_execute"
    assert permission_for_action("chat.run", "project") == "run_agent"
    assert permission_for_action("chat.run", "session") == "run"

    with pytest.raises(ValueError, match="unknown product permission"):
        permission_for_action("memory.personal.read", "team")


def test_check_and_batch_check_delegate_to_transport_and_fail_closed():
    from team_cloud.authz.spicedb import (
        PermissionCheck,
        ResourceRef,
        SpiceDBClient,
        SubjectRef,
    )

    transport = FakeSpiceDBTransport()
    client = SpiceDBClient(transport=transport)

    decision = client.check(
        subject=SubjectRef("user", "alice"),
        resource=ResourceRef("memory", "mem-1"),
        action="memory.personal.read",
        consistency="fully_consistent_for_sensitive",
    )

    assert decision.allowed is True
    assert decision.reason == "allowed"
    assert transport.check_calls[-1] == {
        "subject": "user:alice",
        "resource": "memory:mem-1",
        "permission": "read_personal",
        "consistency": "fully_consistent_for_sensitive",
    }

    decisions = client.batch_check(
        [
            PermissionCheck(
                subject=SubjectRef("user", "alice"),
                resource=ResourceRef("tool", "terminal"),
                action="tool.terminal.execute",
            ),
            PermissionCheck(
                subject=SubjectRef("user", "alice"),
                resource=ResourceRef("backup", "backup-1"),
                action="backup.restore",
            ),
        ]
    )
    assert [decision.allowed for decision in decisions] == [True, False]

    failing_client = SpiceDBClient(transport=FakeSpiceDBTransport(fail=True))
    denied = failing_client.check(
        subject=SubjectRef("user", "alice"),
        resource=ResourceRef("memory", "mem-1"),
        action="memory.personal.read",
    )
    assert denied.allowed is False
    assert denied.reason == "spicedb_error"


def test_lookup_resources_delegates_with_mapped_permission():
    from team_cloud.authz.spicedb import ResourceRef, SpiceDBClient, SubjectRef

    transport = FakeSpiceDBTransport()
    client = SpiceDBClient(transport=transport)

    resources = client.lookup_resources(
        subject=SubjectRef("user", "alice"),
        resource_type="memory",
        action="memory.personal.read",
        consistency="fully_consistent_for_sensitive",
    )

    assert resources == (ResourceRef("memory", "allowed-1"), ResourceRef("memory", "allowed-2"))
    assert transport.lookup_calls[-1]["permission"] == "read_personal"


def test_write_relationships_formats_relationships():
    from team_cloud.authz.spicedb import (
        Relationship,
        ResourceRef,
        SpiceDBClient,
        SubjectRef,
    )

    transport = FakeSpiceDBTransport()
    client = SpiceDBClient(transport=transport)

    result = client.write_relationships(
        [
            Relationship(
                resource=ResourceRef("organization", "org-1"),
                relation="member",
                subject=SubjectRef("user", "alice"),
            ),
            Relationship(
                resource=ResourceRef("team", "team-1"),
                relation="service_account",
                subject=SubjectRef("service_account", "ci-runner"),
            ),
        ],
        operation="touch",
    )

    assert result == {"written": 2, "operation": "touch"}
    assert transport.write_calls[-1] == {
        "relationships": [
            "organization:org-1#member@user:alice",
            "team:team-1#service_account@service_account:ci-runner",
        ],
        "operation": "touch",
    }
