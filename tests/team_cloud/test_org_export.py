from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO
import json
from zipfile import ZipFile


NOW = datetime(2026, 5, 22, 12, 0, tzinfo=UTC)


def test_org_export_builds_zip_snapshot_with_org_scoped_data_and_manifest():
    from team_cloud.admin.organizations import InMemoryOrganizationService
    from team_cloud.audit import InMemoryAuditLog
    from team_cloud.authz.outbox import (
        InMemoryRelationshipOutboxRepository,
        RelationshipOutboxService,
    )
    from team_cloud.cloud_sessions import InMemoryCloudSessionRepository
    from team_cloud.exports.org import OrganizationExportService
    from team_cloud.memory.service import InMemoryMemoryService

    outbox_repository = InMemoryRelationshipOutboxRepository()
    org_service = InMemoryOrganizationService(outbox_repository=outbox_repository)
    org_service.create_organization(slug="org-1", name="Hermes Labs")
    org_service.create_team(org_id="org-1", slug="platform", name="Platform")
    org_service.invite_member(
        org_id="org-1",
        email="alice@example.com",
        display_name="Alice",
        user_id="alice",
    )
    org_service.create_organization(slug="org-2", name="Other Org")

    relationships = RelationshipOutboxService(outbox_repository)
    relationships.enqueue(
        org_id="org-1",
        aggregate_type="organization",
        aggregate_id="org-1",
        operation="touch",
        relationships=["organization:org-1#member@user:alice"],
        created_at=NOW,
    )
    relationships.enqueue(
        org_id="org-2",
        aggregate_type="organization",
        aggregate_id="org-2",
        operation="touch",
        relationships=["organization:org-2#member@user:bob"],
        created_at=NOW,
    )

    sessions = InMemoryCloudSessionRepository()
    session = sessions.create_session(
        org_id="org-1",
        team_id="org-1:platform",
        project_id="project-1",
        owner_member_id="org-1:alice",
        title="Deploy review",
    )
    sessions.append_message(
        session_id=session["id"],
        org_id="org-1",
        role="user",
        content={"text": "ship it"},
    )
    sessions.append_tool_call(
        session_id=session["id"],
        org_id="org-1",
        actor_member_id="org-1:alice",
        tool_name="terminal",
        risk_level="terminal",
        decision="approved",
        input_redacted={"command": "pytest"},
    )
    sessions.create_session(
        org_id="org-2",
        team_id="team-2",
        project_id="project-other",
        owner_member_id="bob",
        title="Other org",
    )

    memory_service = InMemoryMemoryService()
    memory = memory_service.create_memory(
        {
            "org_id": "org-1",
            "scope": "personal",
            "subject_member_id": "org-1:alice",
            "content": "Alice likes concise exports.",
            "project_id": "project-1",
        }
    )
    memory_service.create_memory(
        {
            "org_id": "org-2",
            "scope": "personal",
            "subject_member_id": "bob",
            "content": "Other org memory.",
        }
    )

    audit_log = InMemoryAuditLog()
    audit_log.record(
        org_id="org-1",
        actor_member_id="org-1:alice",
        action="org.export.requested",
        resource_type="organization",
        resource_id="org-1",
        metadata={"client_secret": "do-not-export", "reason": "portability"},
    )
    audit_log.record(
        org_id="org-2",
        actor_member_id="bob",
        action="other",
        resource_type="organization",
        resource_id="org-2",
    )

    exporter = OrganizationExportService(
        organization_service=org_service,
        cloud_session_repository=sessions,
        memory_service=memory_service,
        relationship_outbox_repository=outbox_repository,
        audit_log=audit_log,
        now=lambda: NOW,
        export_id_factory=lambda: "org-export-1",
    )

    result = exporter.export_org(org_id="org-1", actor_member_id="org-1:alice")

    assert result.export_id == "org-export-1"
    assert result.manifest["object_type"] == "org_export"
    assert result.manifest["org_id"] == "org-1"
    assert result.manifest["counts"] == {
        "organizations": 1,
        "teams": 1,
        "members": 1,
        "projects": 1,
        "sessions": 1,
        "messages": 1,
        "tool_calls": 1,
        "memory_items": 1,
        "memory_events": 1,
        "relationships": 1,
        "audit_events": 1,
    }

    with ZipFile(BytesIO(result.package_bytes)) as archive:
        assert set(archive.namelist()) == {
            "manifest.json",
            "organizations.jsonl",
            "teams.jsonl",
            "members.jsonl",
            "projects.jsonl",
            "sessions.jsonl",
            "messages.jsonl",
            "tool_calls.jsonl",
            "memory_items.jsonl",
            "memory_events.jsonl",
            "relationships.jsonl",
            "audit_events.jsonl",
        }
        package_manifest = json.loads(archive.read("manifest.json"))
        organizations = _jsonl(archive, "organizations.jsonl")
        projects = _jsonl(archive, "projects.jsonl")
        memories = _jsonl(archive, "memory_items.jsonl")
        relationships_export = _jsonl(archive, "relationships.jsonl")
        audit_events = _jsonl(archive, "audit_events.jsonl")

    assert package_manifest["export_id"] == "org-export-1"
    assert organizations == [{"id": "org-1", "name": "Hermes Labs", "slug": "org-1", "status": "active"}]
    assert projects == [{"id": "project-1", "org_id": "org-1"}]
    assert [item["id"] for item in memories] == [memory["id"]]
    assert relationships_export[0]["relationships"] == [
        "organization:org-1#member@user:alice"
    ]
    assert audit_events[0]["metadata"]["client_secret"] == "[REDACTED]"
    assert audit_events[0]["metadata"]["reason"] == "portability"
    assert "org-2" not in result.package_bytes.decode("utf-8", errors="ignore")


def _jsonl(archive: ZipFile, name: str) -> list[dict[str, object]]:
    payload = archive.read(name).decode("utf-8")
    return [json.loads(line) for line in payload.splitlines() if line.strip()]
