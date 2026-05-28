from __future__ import annotations

import os
from pathlib import Path

import pytest


def _client():
    try:
        from starlette.testclient import TestClient
    except ImportError:
        pytest.skip("fastapi/starlette not installed")

    from hermes_cli.web_server import _SESSION_HEADER_NAME, _SESSION_TOKEN, app

    client = TestClient(app)
    client.headers[_SESSION_HEADER_NAME] = _SESSION_TOKEN
    return client


def _make_profile(name: str) -> Path:
    root = Path(os.environ["HERMES_HOME"])
    profile_home = root / "profiles" / name
    profile_home.mkdir(parents=True, exist_ok=True)
    return profile_home


def test_team_bridge_soul_endpoint_uses_requested_profile(monkeypatch):
    profile_home = _make_profile("worker")

    def fake_resolve_soul_state():
        from hermes_constants import get_hermes_home

        return {
            "mode": "local",
            "local_soul": {"content": ""},
            "hermes_home": str(get_hermes_home()),
        }

    monkeypatch.setattr("hermes_cli.team_soul.resolve_soul_state", fake_resolve_soul_state)

    response = _client().get("/api/soul/status?profile=worker")

    assert response.status_code == 200
    assert response.json()["hermes_home"] == str(profile_home)


def test_team_bridge_cloud_backup_endpoint_uses_requested_profile(monkeypatch):
    profile_home = _make_profile("backup-worker")

    def fake_cloud_backup_status(*, print_fn):
        from hermes_constants import get_hermes_home

        return {"enabled": True, "hermes_home": str(get_hermes_home())}

    monkeypatch.setattr("hermes_cli.cloud_backup.cloud_backup_status", fake_cloud_backup_status)
    monkeypatch.setattr("hermes_cli.cloud_backup.list_cloud_backups", lambda resource: [])

    response = _client().get("/api/cloud-backup/status?profile=backup-worker&resource=soul")

    assert response.status_code == 200
    assert response.json()["hermes_home"] == str(profile_home)


def test_team_bridge_status_endpoint_uses_requested_profile(monkeypatch):
    profile_home = _make_profile("team-worker")

    def fake_team_status(*, print_fn):
        from hermes_constants import get_hermes_home

        return {"mode": "local", "hermes_home": str(get_hermes_home())}

    monkeypatch.setattr("hermes_cli.team_cloud.team_status", fake_team_status)

    response = _client().get("/api/team/status?profile=team-worker")

    assert response.status_code == 200
    assert response.json()["hermes_home"] == str(profile_home)


def test_team_bridge_management_endpoints_use_requested_profile(monkeypatch):
    profile_home = _make_profile("team-control")
    calls: list[tuple[str, dict]] = []

    def capture(name: str, result: dict):
        def _inner(**kwargs):
            from hermes_constants import get_hermes_home

            calls.append((name, kwargs))
            return {**result, "hermes_home": str(get_hermes_home())}

        return _inner

    monkeypatch.setattr(
        "hermes_cli.team_cloud.connect_team_cloud",
        lambda url, *, print_fn: capture("connect", {"url": url})(url=url),
    )
    monkeypatch.setattr(
        "hermes_cli.team_cloud.login_team_cloud",
        capture("login", {"enabled": True, "default_member_id": "org:alice"}),
    )
    monkeypatch.setattr(
        "hermes_cli.team_cloud.team_use",
        capture("use", {"enabled": True, "default_org_id": "org"}),
    )
    monkeypatch.setattr(
        "hermes_cli.team_cloud.team_off",
        lambda *, print_fn: capture("off", {"enabled": False})(),
    )
    monkeypatch.setattr(
        "hermes_cli.team_cloud.team_logout",
        lambda *, print_fn: capture("logout", {"enabled": False})(),
    )
    monkeypatch.setattr(
        "hermes_cli.team_cloud.team_token_set",
        lambda token, *, print_fn: capture("token", {"saved": True})(token=token),
    )
    monkeypatch.setattr(
        "hermes_cli.team_cloud.team_breaker_status",
        lambda: {"mode": "auto", "state": "closed"},
    )
    monkeypatch.setattr(
        "hermes_cli.team_cloud.team_breaker_open",
        lambda *, print_fn: capture("breaker-open", {"mode": "manual_open"})(),
    )
    monkeypatch.setattr(
        "hermes_cli.team_cloud.team_breaker_close",
        lambda *, print_fn: capture("breaker-close", {"mode": "manual_closed"})(),
    )
    monkeypatch.setattr(
        "hermes_cli.team_cloud.team_breaker_auto",
        lambda *, print_fn: capture("breaker-auto", {"mode": "auto"})(),
    )

    client = _client()
    assert client.post(
        "/api/team/connect?profile=team-control",
        json={"url": "http://team.test"},
    ).json()["hermes_home"] == str(profile_home)
    assert client.post(
        "/api/team/login?profile=team-control",
        json={
            "org": "org",
            "user": "alice",
            "password": "secret",
            "team": "org",
            "project": "default",
        },
    ).json()["default_member_id"] == "org:alice"
    assert client.post(
        "/api/team/use?profile=team-control",
        json={
            "org": "org",
            "team": "org",
            "project": "default",
            "member": "org:alice",
        },
    ).status_code == 200
    assert client.post("/api/team/off?profile=team-control").json()["enabled"] is False
    assert client.post("/api/team/logout?profile=team-control").json()["enabled"] is False
    assert client.post(
        "/api/team/token?profile=team-control",
        json={"token": "hcs_token"},
    ).json()["saved"] is True
    assert client.get("/api/team/breaker?profile=team-control").json()["state"] == "closed"
    assert client.post(
        "/api/team/breaker?profile=team-control",
        json={"action": "open"},
    ).json()["mode"] == "manual_open"
    assert client.post(
        "/api/team/breaker?profile=team-control",
        json={"action": "close"},
    ).json()["mode"] == "manual_closed"
    assert client.post(
        "/api/team/breaker?profile=team-control",
        json={"action": "auto"},
    ).json()["mode"] == "auto"

    assert [name for name, _kwargs in calls] == [
        "connect",
        "login",
        "use",
        "off",
        "logout",
        "token",
        "breaker-open",
        "breaker-close",
        "breaker-auto",
    ]
