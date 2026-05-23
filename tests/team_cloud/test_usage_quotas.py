from __future__ import annotations

from fastapi.testclient import TestClient


class FakeUsageAuthzClient:
    def check(self, **kwargs):
        from team_cloud.authz.spicedb import PermissionDecision

        return PermissionDecision(
            allowed=True,
            reason="allowed",
            subject=kwargs["subject"],
            resource=kwargs["resource"],
            permission="run_agent",
        )


def _usage_sources():
    from team_cloud.chat import InMemoryChatRunService
    from team_cloud.cloud_sessions import InMemoryCloudSessionRepository
    from team_cloud.storage.minio import InMemoryObjectStore, ObjectManifestService

    cloud_sessions = InMemoryCloudSessionRepository()
    chat_runs = InMemoryChatRunService(cloud_session_repository=cloud_sessions)
    manifest_service = ObjectManifestService(object_store=InMemoryObjectStore())
    return cloud_sessions, chat_runs, manifest_service


def _seed_usage_sources():
    from datetime import UTC, datetime

    cloud_sessions, chat_runs, manifest_service = _usage_sources()
    run = chat_runs.create_run(
        org_id="org-1",
        team_id="team-1",
        project_id="project-1",
        member_id="alice",
        message="Summarize quota plan.",
    )
    cloud_sessions.append_message(
        session_id=run["cloud_session_id"],
        org_id="org-1",
        role="assistant",
        content={"text": "Done."},
        run_id=run["id"],
        token_count=42,
    )
    cloud_sessions.append_tool_call(
        session_id=run["cloud_session_id"],
        org_id="org-1",
        actor_member_id="alice",
        tool_name="team_memory_search",
        risk_level="safe",
        decision="allowed",
        input_redacted={"query": "quota"},
        run_id=run["id"],
    )
    manifest_service.upload_object(
        object_type="personal_backup",
        org_id="org-1",
        owner_member_id="alice",
        object_id="backup-1",
        content=b"x" * 128,
        content_type="application/zip",
        created_at=datetime(2026, 5, 22, 12, 0, tzinfo=UTC),
    )
    manifest_service.upload_object(
        object_type="personal_backup",
        org_id="org-2",
        owner_member_id="bob",
        object_id="backup-other-org",
        content=b"y" * 256,
        content_type="application/zip",
        created_at=datetime(2026, 5, 22, 12, 0, tzinfo=UTC),
    )
    return cloud_sessions, chat_runs, manifest_service, run


def test_usage_service_summarizes_runs_tokens_tool_calls_and_backup_bytes():
    from team_cloud.usage import UsageQuotaService

    cloud_sessions, chat_runs, manifest_service, _run = _seed_usage_sources()
    service = UsageQuotaService(
        cloud_session_repository=cloud_sessions,
        chat_run_service=chat_runs,
        object_manifest_service=manifest_service,
    )

    summary = service.org_summary("org-1")

    assert summary["usage"] == {
        "run_count": 1,
        "message_count": 2,
        "token_count": 42,
        "tool_call_count": 1,
        "backup_size_bytes": 128,
    }
    assert summary["quota_status"] == "within_quota"
    assert summary["violations"] == []


def test_usage_quota_service_flags_violations_and_next_run_quota():
    from team_cloud.usage import UsageQuotaService

    cloud_sessions, chat_runs, manifest_service, _run = _seed_usage_sources()
    service = UsageQuotaService(
        cloud_session_repository=cloud_sessions,
        chat_run_service=chat_runs,
        object_manifest_service=manifest_service,
    )
    service.set_org_quotas(
        "org-1",
        run_count=1,
        token_count=40,
        tool_call_count=0,
        backup_size_bytes=100,
    )

    summary = service.org_summary("org-1")
    next_run = service.check_next_run("org-1")

    assert summary["quota_status"] == "over_quota"
    assert {violation["code"] for violation in summary["violations"]} == {
        "token_count_quota_exceeded",
        "tool_call_count_quota_exceeded",
        "backup_size_bytes_quota_exceeded",
    }
    assert next_run["allowed"] is False
    assert next_run["violations"] == [
        {
            "code": "run_count_quota_exceeded",
            "metric": "run_count",
            "limit": 1,
            "actual": 2,
        }
    ]


def test_usage_quota_api_returns_summary_updates_quotas_and_blocks_chat_run():
    from team_cloud.api import create_app
    from team_cloud.usage import UsageQuotaService

    cloud_sessions, chat_runs, manifest_service = _usage_sources()
    service = UsageQuotaService(
        cloud_session_repository=cloud_sessions,
        chat_run_service=chat_runs,
        object_manifest_service=manifest_service,
    )
    client = TestClient(
        create_app(
            authz_client=FakeUsageAuthzClient(),
            cloud_session_repository=cloud_sessions,
            chat_run_service=chat_runs,
            usage_quota_service=service,
            oidc_client=object(),
        )
    )

    updated = client.put(
        "/api/usage/orgs/org-1/quotas",
        json={"run_count": 0, "token_count": 100},
    )
    summary = client.get("/api/usage/orgs/org-1/summary")
    run_response = client.post(
        "/api/chat/runs",
        json={
            "org_id": "org-1",
            "team_id": "team-1",
            "project_id": "project-1",
            "member_id": "alice",
            "message": "This should be blocked by quota.",
        },
    )

    assert updated.status_code == 200
    assert updated.json()["quotas"]["run_count"] == 0
    assert summary.status_code == 200
    assert summary.json()["usage"]["run_count"] == 0
    assert run_response.status_code == 429
    assert run_response.json()["detail"] == "quota_exceeded"
    assert run_response.json()["violations"][0]["code"] == "run_count_quota_exceeded"


def test_web_admin_shell_contains_usage_quota_controls():
    from pathlib import Path

    html = Path("deploy/team-cloud/web-shell/index.html").read_text(encoding="utf-8")

    assert 'data-admin-tab="usage"' in html
    assert 'id="usage-summary"' in html
    assert 'id="usage-quota-form"' in html
    assert 'id="usage-run-count-quota"' in html
    assert 'id="usage-token-count-quota"' in html
    assert 'id="usage-tool-call-count-quota"' in html
    assert 'id="usage-backup-size-bytes-quota"' in html
