from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient


WEB_SHELL = Path("deploy/team-cloud/web-shell/index.html")


class FakeChatAuthzClient:
    def __init__(self, *, allowed: bool = True, fail: bool = False):
        self.allowed = allowed
        self.fail = fail
        self.calls = []

    def check(self, **kwargs):
        self.calls.append(kwargs)
        if self.fail:
            raise RuntimeError("spicedb unavailable")
        from team_cloud.authz.spicedb import PermissionDecision

        return PermissionDecision(
            allowed=self.allowed,
            reason="allowed" if self.allowed else "denied",
            subject=kwargs["subject"],
            resource=kwargs["resource"],
            permission="run_agent",
        )


def test_chat_submit_api_checks_chat_run_permission_and_creates_agent_run():
    from team_cloud.api import create_app

    authz_client = FakeChatAuthzClient()
    client = TestClient(create_app(authz_client=authz_client, oidc_client=object()))

    response = client.post(
        "/api/chat/runs",
        json={
            "org_id": "org-1",
            "team_id": "team-1",
            "project_id": "project-1",
            "member_id": "alice",
            "message": "Summarize team memory.",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "queued"
    assert body["org_id"] == "org-1"
    assert body["team_id"] == "team-1"
    assert body["project_id"] == "project-1"
    assert body["member_id"] == "alice"
    assert body["message"] == "Summarize team memory."
    assert body["events"][0]["type"] == "chat.run.created"
    assert authz_client.calls[-1]["subject"].as_spicedb() == "user:alice"
    assert authz_client.calls[-1]["resource"].as_spicedb() == "project:project-1"
    assert authz_client.calls[-1]["action"] == "chat.run"


def test_chat_submit_api_fails_closed_when_permission_denied():
    from team_cloud.api import create_app

    client = TestClient(
        create_app(
            authz_client=FakeChatAuthzClient(allowed=False),
            oidc_client=object(),
        )
    )

    response = client.post(
        "/api/chat/runs",
        json={
            "org_id": "org-1",
            "team_id": "team-1",
            "project_id": "project-1",
            "member_id": "alice",
            "message": "Run agent.",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "permission_denied"


def test_chat_events_api_returns_agent_run_event_view():
    from team_cloud.api import create_app

    client = TestClient(create_app(authz_client=FakeChatAuthzClient(), oidc_client=object()))
    run = client.post(
        "/api/chat/runs",
        json={
            "org_id": "org-1",
            "team_id": "team-1",
            "project_id": "project-1",
            "member_id": "alice",
            "message": "Run agent.",
        },
    ).json()

    response = client.get(f"/api/chat/runs/{run['id']}/events")

    assert response.status_code == 200
    assert response.json()["items"] == run["events"]


def test_web_chat_entry_has_submit_stream_and_error_surfaces():
    html = WEB_SHELL.read_text(encoding="utf-8")

    assert 'data-admin-tab="chat"' in html
    assert 'id="chat-panel"' in html
    assert 'id="chat-submit-form"' in html
    assert 'id="chat-project-id"' in html
    assert 'id="chat-member-id"' in html
    assert 'id="chat-message"' in html
    assert 'id="chat-run-status"' in html
    assert 'id="chat-event-list"' in html
    assert 'id="chat-error"' in html
    assert "/api/chat/runs" in html
    assert "submitChatRun" in html
    assert "loadChatRunEvents" in html
    assert "renderChatEvents" in html
