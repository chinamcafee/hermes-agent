from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient


def _set_created_at(event: dict[str, object], timestamp: str) -> dict[str, object]:
    event["created_at"] = timestamp
    return event


def test_audit_log_query_filters_actor_resource_decision_and_time_range():
    from team_cloud.audit import InMemoryAuditLog

    audit = InMemoryAuditLog()
    matching = _set_created_at(
        audit.record(
            action="memory.read",
            org_id="org-1",
            actor_member_id="alice",
            actor_type="human",
            resource_type="memory",
            resource_id="mem-1",
            decision="allowed",
            metadata={"scope": "personal", "sensitivity": "restricted"},
        ),
        "2026-05-22T09:15:00Z",
    )
    _set_created_at(
        audit.record(
            action="memory.read",
            org_id="org-1",
            actor_member_id="bob",
            actor_type="human",
            resource_type="memory",
            resource_id="mem-1",
            decision="allowed",
        ),
        "2026-05-22T09:20:00Z",
    )
    _set_created_at(
        audit.record(
            action="memory.read",
            org_id="org-1",
            actor_member_id="alice",
            actor_type="human",
            resource_type="memory",
            resource_id="mem-2",
            decision="denied",
        ),
        "2026-05-22T11:00:00Z",
    )

    results = audit.query(
        org_id="org-1",
        actor_member_id="alice",
        resource_type="memory",
        resource_id="mem-1",
        decision="allowed",
        created_after="2026-05-22T09:00:00Z",
        created_before="2026-05-22T10:00:00Z",
    )

    assert [event["id"] for event in results] == [matching["id"]]


def test_audit_api_exposes_advanced_filters_and_jsonl_export_without_self_audit():
    from team_cloud.api import create_app
    from team_cloud.audit import InMemoryAuditLog

    audit = InMemoryAuditLog()
    exported = _set_created_at(
        audit.record(
            action="memory.read",
            org_id="org-1",
            actor_member_id="alice",
            actor_type="human",
            resource_type="memory",
            resource_id="mem-1",
            decision="allowed",
            metadata={
                "scope": "personal",
                "sensitivity": "restricted",
                "api_key": "secret-value",
            },
        ),
        "2026-05-22T09:15:00Z",
    )
    _set_created_at(
        audit.record(
            action="memory.write",
            org_id="org-1",
            actor_member_id="alice",
            actor_type="human",
            resource_type="memory",
            resource_id="mem-2",
            decision="allowed",
        ),
        "2026-05-22T09:30:00Z",
    )
    client = TestClient(create_app(audit_log=audit, oidc_client=object()))

    list_response = client.get(
        "/api/audit/events",
        params={
            "org_id": "org-1",
            "actor_member_id": "alice",
            "resource_type": "memory",
            "resource_id": "mem-1",
            "decision": "allowed",
            "created_after": "2026-05-22T09:00:00Z",
            "created_before": "2026-05-22T10:00:00Z",
        },
    )
    export_response = client.get(
        "/api/audit/export",
        params={
            "org_id": "org-1",
            "actor_member_id": "alice",
            "resource_type": "memory",
            "resource_id": "mem-1",
            "decision": "allowed",
            "created_after": "2026-05-22T09:00:00Z",
            "created_before": "2026-05-22T10:00:00Z",
        },
    )

    assert list_response.status_code == 200
    assert [event["id"] for event in list_response.json()["items"]] == [exported["id"]]
    assert export_response.status_code == 200
    assert export_response.headers["content-type"].startswith("application/x-ndjson")
    exported_lines = [
        json.loads(line)
        for line in export_response.text.splitlines()
        if line.strip()
    ]
    assert [event["id"] for event in exported_lines] == [exported["id"]]
    assert exported_lines[0]["metadata"]["api_key"] == "[REDACTED]"
    assert len(audit.events) == 2


def test_audit_api_returns_sensitive_read_and_high_risk_tool_views():
    from team_cloud.api import create_app
    from team_cloud.audit import InMemoryAuditLog

    audit = InMemoryAuditLog()
    sensitive = audit.record(
        action="memory.read",
        org_id="org-1",
        actor_member_id="alice",
        actor_type="human",
        resource_type="memory",
        resource_id="mem-personal",
        decision="allowed",
        metadata={"scope": "personal", "sensitivity": "restricted"},
    )
    high_risk = audit.record(
        action="tool.call.approved",
        org_id="org-1",
        actor_member_id="alice",
        actor_type="human",
        resource_type="tool",
        resource_id="terminal",
        decision="approved",
        metadata={"tool_name": "terminal", "cloud_risk_level": "terminal"},
    )
    audit.record(
        action="tool.call.allowed",
        org_id="org-1",
        actor_member_id="alice",
        actor_type="human",
        resource_type="tool",
        resource_id="web_search",
        decision="allowed",
        metadata={"tool_name": "web_search", "cloud_risk_level": "network"},
    )
    client = TestClient(create_app(audit_log=audit, oidc_client=object()))

    sensitive_response = client.get("/api/audit/sensitive-reads", params={"org_id": "org-1"})
    tool_response = client.get("/api/audit/high-risk-tools", params={"org_id": "org-1"})

    assert sensitive_response.status_code == 200
    assert [event["id"] for event in sensitive_response.json()["items"]] == [sensitive["id"]]
    assert tool_response.status_code == 200
    assert [event["id"] for event in tool_response.json()["items"]] == [high_risk["id"]]
    assert len(audit.events) == 3


def test_web_admin_shell_contains_audit_advanced_controls():
    html = Path("deploy/team-cloud/web-shell/index.html").read_text(encoding="utf-8")

    assert 'data-admin-tab="audit"' in html
    assert 'id="audit-filter-form"' in html
    assert 'id="audit-actor-member-id"' in html
    assert 'id="audit-resource-type"' in html
    assert 'id="audit-decision"' in html
    assert 'id="audit-created-after"' in html
    assert 'id="audit-created-before"' in html
    assert 'id="audit-events-table-body"' in html
    assert 'id="audit-sensitive-reads"' in html
    assert 'id="audit-high-risk-tools"' in html
    assert 'id="audit-export-button"' in html
