from __future__ import annotations

from fastapi.testclient import TestClient


class FakeHistoryAuthzClient:
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

    return TestClient(create_app(authz_client=FakeHistoryAuthzClient(), oidc_client=object()))


def _create_run(
    client: TestClient,
    *,
    org_id: str = "org-1",
    team_id: str = "team-1",
    project_id: str = "project-1",
    member_id: str = "alice",
    message: str = "Summarize roadmap decisions.",
) -> dict:
    response = client.post(
        "/api/chat/runs",
        json={
            "org_id": org_id,
            "team_id": team_id,
            "project_id": project_id,
            "member_id": member_id,
            "message": message,
        },
    )
    assert response.status_code == 201
    return response.json()


def test_chat_submit_writes_cloud_session_and_user_message():
    client = _client()

    run = _create_run(client, message="Summarize roadmap decisions.")

    assert run["cloud_session_id"].startswith("cloud-session-")
    response = client.get(f"/api/cloud/sessions/{run['cloud_session_id']}")

    assert response.status_code == 200
    history = response.json()
    assert history["id"] == run["cloud_session_id"]
    assert history["org_id"] == "org-1"
    assert history["team_id"] == "team-1"
    assert history["project_id"] == "project-1"
    assert history["owner_member_id"] == "alice"
    assert history["messages"][0]["role"] == "user"
    assert history["messages"][0]["content"] == {"text": "Summarize roadmap decisions."}
    assert history["messages"][0]["run_id"] == run["id"]


def test_cloud_sessions_list_filters_by_org_project_member_and_query():
    client = _client()
    first = _create_run(client, message="Summarize roadmap decisions.")
    _create_run(
        client,
        org_id="org-1",
        team_id="team-1",
        project_id="project-2",
        member_id="bob",
        message="Draft release notes.",
    )

    response = client.get(
        "/api/cloud/sessions",
        params={
            "org_id": "org-1",
            "project_id": "project-1",
            "member_id": "alice",
            "q": "roadmap",
        },
    )

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == [
        first["cloud_session_id"]
    ]


def test_cloud_session_history_records_tool_calls_for_runtime_events():
    client = _client()
    run = _create_run(client)

    created = client.post(
        f"/api/cloud/sessions/{run['cloud_session_id']}/tool-calls",
        json={
            "org_id": "org-1",
            "run_id": run["id"],
            "actor_member_id": "alice",
            "tool_name": "team_memory_search",
            "risk_level": "safe",
            "decision": "allowed",
            "input_redacted": {"query": "roadmap"},
            "output_redacted": {"memory_ids": ["mem-1"]},
        },
    )
    history = client.get(f"/api/cloud/sessions/{run['cloud_session_id']}").json()

    assert created.status_code == 201
    assert history["tool_calls"][0]["run_id"] == run["id"]
    assert history["tool_calls"][0]["tool_name"] == "team_memory_search"
    assert history["tool_calls"][0]["decision"] == "allowed"
    assert history["tool_calls"][0]["input_redacted"] == {"query": "roadmap"}
    assert history["tool_calls"][0]["output_redacted"] == {"memory_ids": ["mem-1"]}
