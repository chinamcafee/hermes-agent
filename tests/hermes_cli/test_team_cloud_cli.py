from __future__ import annotations

from unittest.mock import patch


class FakeTeamCloudClient:
    def __init__(self) -> None:
        self.login_payload = None
        self.status_called = False
        self.session_token = ""

    def bootstrap_status(self):
        self.status_called = True
        return {
            "service": "hermes-team-cloud-go",
            "status": "ready",
            "initialized": True,
            "organization_count": 1,
            "super_admin_count": 1,
        }

    def login(self, *, org_id: str, user_id: str, password: str):
        self.login_payload = {
            "org_id": org_id,
            "user_id": user_id,
            "password": password,
        }
        return {
            "token": "hcs_test_session",
            "expires_at": "2026-05-24T18:00:00Z",
            "member": {
                "id": "hermes-labs:alice",
                "org_id": "hermes-labs",
                "user_id": "alice",
                "role": "user",
                "status": "active",
                "display_name": "Alice",
                "email": "alice@example.com",
            },
        }

    def session(self, token: str):
        self.session_token = token
        return {
            "org_id": "hermes-labs",
            "member_id": "hermes-labs:alice",
            "role": "user",
            "email": "alice@example.com",
        }


class FailingSessionTeamCloudClient(FakeTeamCloudClient):
    def session(self, token: str):
        self.session_token = token
        raise RuntimeError("invalid session")


def test_default_config_contains_team_cloud_section(tmp_path):
    from hermes_cli.config import DEFAULT_CONFIG, load_config

    with patch.dict("os.environ", {"HERMES_HOME": str(tmp_path)}):
        config = load_config()

    assert DEFAULT_CONFIG["team_cloud"]["enabled"] is False
    assert config["team_cloud"]["url"] == ""
    assert config["team_cloud"]["token_env"] == "HERMES_TEAM_CLOUD_SESSION_TOKEN"
    assert "personal_memory_enabled" not in config["team_cloud"]


def test_team_connect_and_login_store_profile_config_and_secret(tmp_path):
    from hermes_cli.config import load_config, load_env
    from hermes_cli.team_cloud import (
        connect_team_cloud,
        login_team_cloud,
        resolve_cli_team_context,
    )

    client = FakeTeamCloudClient()
    messages: list[str] = []
    with patch.dict("os.environ", {"HERMES_HOME": str(tmp_path)}, clear=False):
        connect_team_cloud("http://localhost:8780/", print_fn=messages.append)
        login_team_cloud(
            org_id="hermes-labs",
            user_id="alice",
            password="secret-password",
            team_id="",
            project_id="platform",
            client=client,
            print_fn=messages.append,
        )
        config = load_config()
        env = load_env()
        context = resolve_cli_team_context(config=config, env=env)

    assert client.login_payload == {
        "org_id": "hermes-labs",
        "user_id": "alice",
        "password": "secret-password",
    }
    assert config["team_cloud"]["enabled"] is True
    assert config["team_cloud"]["url"] == "http://localhost:8780"
    assert config["team_cloud"]["default_org_id"] == "hermes-labs"
    assert config["team_cloud"]["default_team_id"] == "hermes-labs"
    assert config["team_cloud"]["default_project_id"] == "platform"
    assert config["team_cloud"]["default_member_id"] == "hermes-labs:alice"
    assert env["HERMES_TEAM_CLOUD_SESSION_TOKEN"] == "hcs_test_session"
    assert context == {
        "org_id": "hermes-labs",
        "team_id": "hermes-labs",
        "project_id": "platform",
        "member_id": "hermes-labs:alice",
    }
    assert any("Team Cloud connected" in message for message in messages)
    assert any("Logged in as hermes-labs:alice" in message for message in messages)


def test_team_status_uses_remote_session_when_token_is_present(tmp_path):
    from hermes_cli.config import save_env_value
    from hermes_cli.team_cloud import connect_team_cloud, login_team_cloud, team_status

    client = FakeTeamCloudClient()
    messages: list[str] = []
    with patch.dict("os.environ", {"HERMES_HOME": str(tmp_path)}, clear=False):
        connect_team_cloud("http://localhost:8780", print_fn=lambda _: None)
        login_team_cloud(
            org_id="hermes-labs",
            user_id="alice",
            password="secret-password",
            team_id="",
            project_id="",
            client=client,
            print_fn=lambda _: None,
        )
        save_env_value("HERMES_TEAM_CLOUD_SESSION_TOKEN", "hcs_test_session")
        team_status(client=client, print_fn=messages.append)

    assert client.status_called is True
    assert client.session_token == "hcs_test_session"
    rendered = "\n".join(messages)
    assert "mode: team" in rendered
    assert "remote: ready" in rendered
    assert "member: hermes-labs:alice" in rendered


def test_team_status_requires_successful_member_session_for_team_mode(tmp_path):
    from hermes_cli.config import save_env_value
    from hermes_cli.team_cloud import connect_team_cloud, login_team_cloud, team_status

    client = FailingSessionTeamCloudClient()
    with patch.dict("os.environ", {"HERMES_HOME": str(tmp_path)}, clear=False):
        connect_team_cloud("http://localhost:8780", print_fn=lambda _: None)
        login_team_cloud(
            org_id="hermes-labs",
            user_id="alice",
            password="secret-password",
            client=FakeTeamCloudClient(),
            print_fn=lambda _: None,
        )
        save_env_value("HERMES_TEAM_CLOUD_SESSION_TOKEN", "stale-token")
        status = team_status(client=client, print_fn=lambda _: None)

    assert status["mode"] == "local"
    assert status["connection_configured"] is True
    assert status["account_authenticated"] is False
    assert status["login_required"] is True
    assert status["session"]["error"] == "invalid session"


def test_team_slash_command_is_registered():
    from hermes_cli.commands import resolve_command

    command = resolve_command("team")
    assert command is not None
    assert command.name == "team"
    assert command.cli_only is True


def test_team_cloud_auto_circuit_breaker_blocks_context_after_failures(tmp_path):
    from hermes_cli.config import load_config
    from hermes_cli.team_cloud import (
        connect_team_cloud,
        login_team_cloud,
        record_team_cloud_failure,
        resolve_cli_team_context,
        team_breaker_close,
        team_breaker_status,
    )

    client = FakeTeamCloudClient()
    with patch.dict("os.environ", {"HERMES_HOME": str(tmp_path)}, clear=False):
        connect_team_cloud("http://localhost:8780", print_fn=lambda _: None)
        login_team_cloud(
            org_id="hermes-labs",
            user_id="alice",
            password="secret-password",
            client=client,
            print_fn=lambda _: None,
        )
        assert resolve_cli_team_context(config=load_config()) is not None

        record_team_cloud_failure("connection refused")
        record_team_cloud_failure("connection refused")
        record_team_cloud_failure("connection refused")

        status = team_breaker_status()
        assert status["mode"] == "auto"
        assert status["state"] == "open"
        assert status["failure_count"] == 3
        assert resolve_cli_team_context(config=load_config()) is None

        team_breaker_close(print_fn=lambda _: None)
        assert team_breaker_status()["mode"] == "manual_closed"
        assert resolve_cli_team_context(config=load_config()) is not None


def test_team_breaker_slash_commands_update_manual_state(tmp_path):
    from hermes_cli.team_cloud import handle_team_slash, team_breaker_status

    messages: list[str] = []
    with patch.dict("os.environ", {"HERMES_HOME": str(tmp_path)}, clear=False):
        handle_team_slash("/team breaker open", print_fn=messages.append)
        assert team_breaker_status()["mode"] == "manual_open"

        handle_team_slash("/team breaker auto", print_fn=messages.append)
        assert team_breaker_status()["mode"] == "auto"

    rendered = "\n".join(messages)
    assert "Team Cloud API breaker: open" in rendered
    assert "Team Cloud API breaker: auto" in rendered


def test_team_status_label_distinguishes_local_team_and_paused_states(tmp_path):
    from hermes_cli.team_cloud import (
        connect_team_cloud,
        login_team_cloud,
        team_breaker_open,
        team_cli_status_label,
    )

    client = FakeTeamCloudClient()
    with patch.dict("os.environ", {"HERMES_HOME": str(tmp_path)}, clear=False):
        assert team_cli_status_label()["label"] == "Local"
        connect_team_cloud("http://localhost:8780", print_fn=lambda _: None)
        login_team_cloud(
            org_id="hermes-labs",
            user_id="alice",
            password="secret-password",
            client=client,
            print_fn=lambda _: None,
        )
        assert team_cli_status_label()["label"] == "Team hermes-labs:alice"

        team_breaker_open(print_fn=lambda _: None)
        paused = team_cli_status_label()

    assert paused["mode"] == "paused"
    assert paused["label"] == "Team API paused"
