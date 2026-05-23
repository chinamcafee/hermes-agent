from __future__ import annotations

from datetime import UTC, datetime


NOW = datetime(2026, 5, 22, 15, 0, tzinfo=UTC)
OLD = "2026-01-01T00:00:00Z"
RECENT = "2026-05-20T00:00:00Z"


def _fixture():
    from team_cloud.audit import InMemoryAuditLog
    from team_cloud.cloud_sessions import InMemoryCloudSessionRepository
    from team_cloud.memory.service import InMemoryMemoryService

    sessions = InMemoryCloudSessionRepository()
    old_session = sessions.create_session(
        org_id="org-1",
        team_id="team-1",
        project_id="project-1",
        owner_member_id="member-1",
        title="old session",
    )
    recent_session = sessions.create_session(
        org_id="org-1",
        team_id="team-1",
        project_id="project-1",
        owner_member_id="member-1",
        title="recent session",
    )
    old_tool_call = sessions.append_tool_call(
        session_id=old_session["id"],
        org_id="org-1",
        actor_member_id="member-1",
        tool_name="terminal",
        risk_level="terminal",
        decision="approved",
        input_redacted={"cmd": "old"},
    )
    recent_tool_call = sessions.append_tool_call(
        session_id=recent_session["id"],
        org_id="org-1",
        actor_member_id="member-1",
        tool_name="web_search",
        risk_level="network",
        decision="allowed",
        input_redacted={"q": "recent"},
    )
    sessions._sessions[old_session["id"]]["updated_at"] = OLD
    sessions._sessions[old_session["id"]]["created_at"] = OLD
    sessions._sessions[old_session["id"]]["tool_calls"][0]["created_at"] = OLD
    sessions._sessions[recent_session["id"]]["updated_at"] = RECENT
    sessions._sessions[recent_session["id"]]["tool_calls"][0]["created_at"] = RECENT

    memory_service = InMemoryMemoryService()
    old_memory = memory_service.create_memory(
        {
            "org_id": "org-1",
            "scope": "personal",
            "subject_member_id": "member-1",
            "content": "old memory",
        }
    )
    held_memory = memory_service.create_memory(
        {
            "org_id": "org-1",
            "scope": "personal",
            "subject_member_id": "member-1",
            "content": "held memory",
        }
    )
    recent_memory = memory_service.create_memory(
        {
            "org_id": "org-1",
            "scope": "personal",
            "subject_member_id": "member-1",
            "content": "recent memory",
        }
    )
    memory_service.items[old_memory["id"]]["updated_at"] = OLD
    memory_service.items[held_memory["id"]]["updated_at"] = OLD
    memory_service.items[held_memory["id"]]["legal_hold"] = True
    memory_service.items[recent_memory["id"]]["updated_at"] = RECENT

    audit_log = InMemoryAuditLog()
    old_audit = audit_log.record(
        org_id="org-1",
        action="session.read",
        resource_type="cloud_session",
        resource_id=old_session["id"],
    )
    recent_audit = audit_log.record(
        org_id="org-1",
        action="memory.write",
        resource_type="memory_item",
        resource_id=recent_memory["id"],
    )
    held_audit = audit_log.record(
        org_id="org-1",
        action="break_glass.read",
        resource_type="memory_item",
        resource_id=held_memory["id"],
        metadata={"legal_hold": True},
    )
    old_audit["created_at"] = OLD
    recent_audit["created_at"] = RECENT
    held_audit["created_at"] = OLD

    return {
        "sessions": sessions,
        "memory_service": memory_service,
        "audit_log": audit_log,
        "old_session": old_session,
        "recent_session": recent_session,
        "old_tool_call": old_tool_call,
        "recent_tool_call": recent_tool_call,
        "old_memory": old_memory,
        "held_memory": held_memory,
        "recent_memory": recent_memory,
        "old_audit": old_audit,
        "recent_audit": recent_audit,
        "held_audit": held_audit,
    }


def test_retention_policy_plans_expired_records_and_skips_legal_hold():
    from team_cloud.retention import RetentionPolicyService

    fixture = _fixture()
    service = RetentionPolicyService(now=lambda: NOW)
    service.upsert_policy(
        org_id="org-1",
        resource_type="session",
        retain_for_days=30,
        action="soft_delete",
    )
    service.upsert_policy(
        org_id="org-1",
        resource_type="tool_call",
        retain_for_days=7,
        action="hard_delete",
    )
    service.upsert_policy(
        org_id="org-1",
        resource_type="memory",
        retain_for_days=90,
        action="archive",
    )
    service.upsert_policy(
        org_id="org-1",
        resource_type="audit_event",
        retain_for_days=90,
        action="hard_delete",
    )

    plan = service.plan_retention(
        org_id="org-1",
        cloud_session_repository=fixture["sessions"],
        memory_service=fixture["memory_service"],
        audit_log=fixture["audit_log"],
    )

    assert {
        (item["resource_type"], item["resource_id"], item["action"])
        for item in plan["actions"]
    } == {
        ("session", fixture["old_session"]["id"], "soft_delete"),
        ("tool_call", fixture["old_tool_call"]["id"], "hard_delete"),
        ("memory", fixture["old_memory"]["id"], "archive"),
        ("audit_event", fixture["old_audit"]["id"], "hard_delete"),
    }
    assert {
        (item["resource_type"], item["resource_id"], item["reason"])
        for item in plan["skipped"]
    } == {
        ("memory", fixture["held_memory"]["id"], "legal_hold"),
        ("audit_event", fixture["held_audit"]["id"], "legal_hold"),
    }
    assert all(item["org_id"] == "org-1" for item in plan["actions"])


def test_retention_policy_apply_updates_repositories_and_writes_audit():
    from team_cloud.retention import RetentionPolicyService

    fixture = _fixture()
    service = RetentionPolicyService(audit_log=fixture["audit_log"], now=lambda: NOW)
    for resource_type, retain_for_days, action in (
        ("session", 30, "soft_delete"),
        ("tool_call", 7, "hard_delete"),
        ("memory", 90, "archive"),
        ("audit_event", 90, "hard_delete"),
    ):
        service.upsert_policy(
            org_id="org-1",
            resource_type=resource_type,
            retain_for_days=retain_for_days,
            action=action,
        )
    plan = service.plan_retention(
        org_id="org-1",
        cloud_session_repository=fixture["sessions"],
        memory_service=fixture["memory_service"],
        audit_log=fixture["audit_log"],
    )

    summary = service.apply_retention(
        plan["actions"],
        cloud_session_repository=fixture["sessions"],
        memory_service=fixture["memory_service"],
        audit_log=fixture["audit_log"],
    )

    assert summary == {"applied": 4, "failed": 0}
    assert fixture["sessions"]._sessions[fixture["old_session"]["id"]]["status"] == "deleted"
    assert fixture["sessions"]._sessions[fixture["recent_session"]["id"]]["status"] == "active"
    assert fixture["sessions"]._sessions[fixture["old_session"]["id"]]["tool_calls"] == []
    assert fixture["sessions"]._sessions[fixture["recent_session"]["id"]]["tool_calls"][0][
        "id"
    ] == fixture["recent_tool_call"]["id"]
    assert fixture["memory_service"].items[fixture["old_memory"]["id"]]["status"] == "archived"
    assert fixture["memory_service"].items[fixture["held_memory"]["id"]]["status"] == "active"
    assert fixture["old_audit"]["id"] not in {
        event["id"] for event in fixture["audit_log"].events
    }
    assert fixture["held_audit"]["id"] in {
        event["id"] for event in fixture["audit_log"].events
    }
    assert fixture["audit_log"].events[-1]["action"] == "data_retention.applied"


def test_retention_policy_rejects_invalid_policy_values():
    import pytest

    from team_cloud.retention import RetentionPolicyService

    service = RetentionPolicyService(now=lambda: NOW)

    with pytest.raises(ValueError, match="invalid_retention_resource_type"):
        service.upsert_policy(
            org_id="org-1",
            resource_type="backup",
            retain_for_days=30,
            action="hard_delete",
        )
    with pytest.raises(ValueError, match="invalid_retention_days"):
        service.upsert_policy(
            org_id="org-1",
            resource_type="session",
            retain_for_days=0,
            action="soft_delete",
        )
    with pytest.raises(ValueError, match="invalid_retention_action"):
        service.upsert_policy(
            org_id="org-1",
            resource_type="memory",
            retain_for_days=30,
            action="purge",
        )
