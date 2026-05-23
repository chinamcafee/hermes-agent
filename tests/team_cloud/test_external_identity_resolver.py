from __future__ import annotations

from fastapi.testclient import TestClient


def test_external_identity_resolver_returns_team_context_for_bound_platform_user():
    from team_cloud.api import create_app
    from team_cloud.identity import InMemoryExternalIdentityResolver

    resolver = InMemoryExternalIdentityResolver()
    resolver.bind(
        platform="telegram",
        external_user_id="tg-alice",
        org_id="org-1",
        team_id="team-1",
        member_id="alice",
        project_id="project-1",
        external_team_id="workspace-1",
    )
    client = TestClient(
        create_app(external_identity_resolver=resolver, oidc_client=object())
    )

    response = client.post(
        "/v1/external-identities/resolve",
        json={
            "platform": "telegram",
            "external_user_id": "tg-alice",
            "external_team_id": "workspace-1",
            "external_channel_id": "chat-1",
            "chat_type": "dm",
            "shared_session": False,
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "resolved",
        "team_context": {
            "org_id": "org-1",
            "team_id": "team-1",
            "project_id": "project-1",
            "member_id": "alice",
            "personal_memory_enabled": True,
        },
        "session_key_prefix": "team:org-1:team-1",
        "binding_message": None,
    }


def test_external_identity_resolver_returns_binding_prompt_for_unbound_user():
    from team_cloud.api import create_app
    from team_cloud.identity import InMemoryExternalIdentityResolver

    client = TestClient(
        create_app(
            external_identity_resolver=InMemoryExternalIdentityResolver(),
            oidc_client=object(),
        )
    )

    response = client.post(
        "/v1/external-identities/resolve",
        json={
            "platform": "telegram",
            "external_user_id": "tg-unbound",
            "external_team_id": "workspace-1",
            "external_channel_id": "chat-1",
            "chat_type": "dm",
            "shared_session": False,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "unbound"
    assert body["team_context"] is None
    assert body["session_key_prefix"] is None
    assert "binding code" in body["binding_message"]


def test_external_identity_resolver_marks_personal_memory_disabled_for_shared_sessions():
    from team_cloud.api import create_app
    from team_cloud.identity import InMemoryExternalIdentityResolver

    resolver = InMemoryExternalIdentityResolver()
    resolver.bind(
        platform="slack",
        external_user_id="U-alice",
        org_id="org-1",
        team_id="team-1",
        member_id="alice",
        external_team_id="T-workspace",
    )
    client = TestClient(
        create_app(external_identity_resolver=resolver, oidc_client=object())
    )

    response = client.post(
        "/v1/external-identities/resolve",
        json={
            "platform": "slack",
            "external_user_id": "U-alice",
            "external_team_id": "T-workspace",
            "external_channel_id": "C-shared",
            "chat_type": "channel",
            "shared_session": True,
        },
    )

    assert response.status_code == 200
    assert response.json()["team_context"]["personal_memory_enabled"] is False
