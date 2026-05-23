from __future__ import annotations

from fastapi.testclient import TestClient


class FakeLogsTracesAuthzClient:
    def check(self, **kwargs):
        from team_cloud.authz.spicedb import PermissionDecision

        return PermissionDecision(
            allowed=True,
            reason="allowed",
            subject=kwargs["subject"],
            resource=kwargs["resource"],
            permission="run_agent",
        )


def _client(*, audit_log=None) -> TestClient:
    from team_cloud.api import create_app

    return TestClient(
        create_app(
            audit_log=audit_log,
            authz_client=FakeLogsTracesAuthzClient(),
            oidc_client=object(),
        )
    )


def test_correlation_context_prefers_trace_then_run_then_request():
    from team_cloud.correlation import build_correlation_context

    assert build_correlation_context(
        request_id="req-1",
        run_id="run-1",
        trace_id="trace-1",
    ) == {
        "request_id": "req-1",
        "run_id": "run-1",
        "audit_event_id": None,
        "trace_id": "trace-1",
        "correlation_id": "trace-1",
    }
    assert build_correlation_context(request_id="req-2", run_id="run-2")[
        "correlation_id"
    ] == "run-2"
    assert build_correlation_context(request_id="req-3")["correlation_id"] == "req-3"


def test_chat_run_request_audit_and_observability_share_correlation_fields():
    from team_cloud.audit import InMemoryAuditLog

    audit = InMemoryAuditLog()
    client = _client(audit_log=audit)

    response = client.post(
        "/api/chat/runs",
        headers={"x-request-id": "req-p4-05", "x-trace-id": "trace-p4-05"},
        json={
            "org_id": "org-1",
            "team_id": "team-1",
            "project_id": "project-1",
            "member_id": "alice",
            "message": "Trace this run.",
        },
    )

    assert response.status_code == 201
    run = response.json()
    assert run["request_id"] == "req-p4-05"
    assert run["trace_id"] == "trace-p4-05"
    assert run["correlation_id"] == "trace-p4-05"

    run_events = client.get(f"/api/chat/runs/{run['id']}/events").json()["items"]
    assert run_events[0]["request_id"] == "req-p4-05"
    assert run_events[0]["run_id"] == run["id"]
    assert run_events[0]["trace_id"] == "trace-p4-05"
    assert run_events[0]["correlation_id"] == "trace-p4-05"

    audit_events = audit.query(run_id=run["id"], correlation_id="trace-p4-05")
    assert len(audit_events) == 1
    assert audit_events[0]["request_id"] == "req-p4-05"
    assert audit_events[0]["trace_id"] == "trace-p4-05"
    assert audit_events[0]["metadata"]["path"] == "/api/chat/runs"

    observed = [
        event
        for event in client.app.state.observability.events
        if event["path"] == "/api/chat/runs"
    ][-1]
    assert observed["request_id"] == "req-p4-05"
    assert observed["run_id"] == run["id"]
    assert observed["trace_id"] == "trace-p4-05"
    assert observed["correlation_id"] == "trace-p4-05"


def test_runtime_event_bridge_preserves_request_and_trace_correlation():
    client = _client()
    created = client.post(
        "/api/chat/runs",
        headers={"x-request-id": "req-create", "x-trace-id": "trace-create"},
        json={
            "org_id": "org-1",
            "team_id": "team-1",
            "project_id": "project-1",
            "member_id": "alice",
            "message": "Capture runtime events.",
        },
    ).json()

    response = client.post(
        "/api/runtime/events",
        json={
            "org_id": "org-1",
            "run_id": created["id"],
            "cloud_session_id": created["cloud_session_id"],
            "request_id": "req-runtime",
            "trace_id": "trace-runtime",
            "type": "message.completed",
            "payload": {"role": "assistant", "content": "Done."},
        },
    )

    assert response.status_code == 202
    event = response.json()["event"]
    assert event["request_id"] == "req-runtime"
    assert event["trace_id"] == "trace-runtime"
    assert event["correlation_id"] == "trace-runtime"
    assert event["payload"]["request_id"] == "req-runtime"
    assert event["payload"]["trace_id"] == "trace-runtime"
    assert event["payload"]["correlation_id"] == "trace-runtime"
