from __future__ import annotations

from fastapi.testclient import TestClient


class FakeRuntimeAuthzClient:
    def check(self, **kwargs):
        from team_cloud.authz.spicedb import PermissionDecision

        return PermissionDecision(
            allowed=True,
            reason="allowed",
            subject=kwargs["subject"],
            resource=kwargs["resource"],
            permission="run_agent",
        )


def _client() -> TestClient:
    from team_cloud.api import create_app

    return TestClient(create_app(authz_client=FakeRuntimeAuthzClient(), oidc_client=object()))


def _create_run(client: TestClient) -> dict:
    response = client.post(
        "/api/chat/runs",
        json={
            "org_id": "org-1",
            "team_id": "team-1",
            "project_id": "project-1",
            "member_id": "alice",
            "message": "Run the team memory check.",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_runtime_event_bridge_records_assistant_message_and_run_event():
    client = _client()
    run = _create_run(client)

    response = client.post(
        "/api/runtime/events",
        json={
            "org_id": "org-1",
            "run_id": run["id"],
            "cloud_session_id": run["cloud_session_id"],
            "type": "message.completed",
            "payload": {"role": "assistant", "content": "Done."},
        },
    )
    history = client.get(f"/api/cloud/sessions/{run['cloud_session_id']}").json()
    events = client.get(f"/api/chat/runs/{run['id']}/events").json()["items"]

    assert response.status_code == 202
    assert response.json()["accepted"] is True
    assert history["messages"][-1]["role"] == "assistant"
    assert history["messages"][-1]["content"] == {"text": "Done."}
    assert events[-1]["type"] == "message.completed"


def test_runtime_event_bridge_records_tool_completed_event():
    client = _client()
    run = _create_run(client)

    response = client.post(
        "/api/runtime/events",
        json={
            "org_id": "org-1",
            "run_id": run["id"],
            "cloud_session_id": run["cloud_session_id"],
            "type": "tool.completed",
            "payload": {
                "actor_member_id": "alice",
                "tool_name": "team_memory_search",
                "risk_level": "safe",
                "decision": "allowed",
                "input_redacted": {"query": "team policy"},
                "output_redacted": {"memory_ids": ["mem-1"]},
            },
        },
    )
    history = client.get(f"/api/cloud/sessions/{run['cloud_session_id']}").json()
    events = client.get(f"/api/chat/runs/{run['id']}/events").json()["items"]

    assert response.status_code == 202
    assert history["tool_calls"][-1]["tool_name"] == "team_memory_search"
    assert history["tool_calls"][-1]["run_id"] == run["id"]
    assert events[-1]["type"] == "tool.completed"


def test_runtime_event_bridge_fails_closed_for_unknown_cloud_session():
    client = _client()

    response = client.post(
        "/api/runtime/events",
        json={
            "org_id": "org-1",
            "run_id": "run-missing",
            "cloud_session_id": "cloud-session-missing",
            "type": "message.completed",
            "payload": {"role": "assistant", "content": "Nope."},
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "cloud_session_not_found"
