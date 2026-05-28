from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch


class FakeTeamSoulClient:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def get_runtime_team_soul(self, *, token: str, org_id: str, team_id: str):
        self.calls.append({"token": token, "org_id": org_id, "team_id": team_id})
        return dict(self.payload)


def test_team_soul_state_combines_parent_and_local_with_parent_precedence(tmp_path):
    from hermes_cli.config import save_env_value
    from hermes_cli.team_cloud import connect_team_cloud, login_team_cloud
    from hermes_cli.team_soul import resolve_soul_state
    from tests.hermes_cli.test_team_cloud_cli import FakeTeamCloudClient

    hermes_home = tmp_path / ".hermes"
    hermes_home.mkdir(parents=True)
    (hermes_home / "SOUL.md").write_text("本地人格：回答要简短。\n", encoding="utf-8")
    client = FakeTeamSoulClient(
        {
            "org_id": "hermes-labs",
            "team_id": "hermes-labs",
            "content": "团队父人格：必须说明我们是闻川网络科技公司。",
            "version": 3,
            "checksum_sha256": "abc123",
        }
    )

    with patch.dict("os.environ", {"HERMES_HOME": str(hermes_home)}, clear=False):
        connect_team_cloud("http://localhost:8780", print_fn=lambda _: None)
        login_team_cloud(
            org_id="hermes-labs",
            user_id="alice",
            password="secret-password",
            client=FakeTeamCloudClient(),
            print_fn=lambda _: None,
        )
        save_env_value("HERMES_TEAM_CLOUD_SESSION_TOKEN", "session-token")
        state = resolve_soul_state(client=client)

    assert client.calls == [{"token": "session-token", "org_id": "hermes-labs", "team_id": "hermes-labs"}]
    assert state["mode"] == "team"
    assert state["team_parent_soul"]["content"] == "团队父人格：必须说明我们是闻川网络科技公司。"
    assert state["local_soul"]["content"] == "本地人格：回答要简短。\n"
    assert state["effective_soul"]["merge_status"] == "safe_fallback"
    assert state["effective_soul"]["content"].index("团队父人格") < state["effective_soul"]["content"].index("本地人格")


def test_team_soul_state_stays_in_team_mode_when_parent_is_not_configured(tmp_path):
    from hermes_cli.config import save_env_value
    from hermes_cli.team_cloud import connect_team_cloud, login_team_cloud
    from hermes_cli.team_soul import resolve_soul_state
    from tests.hermes_cli.test_team_cloud_cli import FakeTeamCloudClient

    hermes_home = tmp_path / ".hermes"
    hermes_home.mkdir(parents=True)
    (hermes_home / "SOUL.md").write_text("本地人格：回答要简短。\n", encoding="utf-8")
    client = FakeTeamSoulClient(
        {
            "org_id": "hermes-labs",
            "team_id": "hermes-labs",
            "content": "",
            "version": 0,
        }
    )

    with patch.dict("os.environ", {"HERMES_HOME": str(hermes_home)}, clear=False):
        connect_team_cloud("http://localhost:8780", print_fn=lambda _: None)
        login_team_cloud(
            org_id="hermes-labs",
            user_id="alice",
            password="secret-password",
            client=FakeTeamCloudClient(),
            print_fn=lambda _: None,
        )
        save_env_value("HERMES_TEAM_CLOUD_SESSION_TOKEN", "session-token")
        state = resolve_soul_state(client=client)

    assert state["mode"] == "team"
    assert state["context"]["member_id"] == "hermes-labs:alice"
    assert state["team_parent_soul"]["content"] == ""
    assert state["effective_soul"]["content"] == "本地人格：回答要简短。"
    assert state["effective_soul"]["merge_status"] == "team_parent_missing"
    assert state["merge"]["status"] == "team_parent_missing"


def test_save_local_soul_triggers_graceful_team_merge_failure_without_provider(tmp_path):
    from hermes_cli.config import save_env_value
    from hermes_cli.team_cloud import connect_team_cloud, login_team_cloud
    from hermes_cli.team_soul import save_local_soul
    from tests.hermes_cli.test_team_cloud_cli import FakeTeamCloudClient

    hermes_home = tmp_path / ".hermes"
    client = FakeTeamSoulClient(
        {
            "org_id": "hermes-labs",
            "team_id": "hermes-labs",
            "content": "团队父人格：必须说明我们是闻川网络科技公司。",
            "version": 1,
            "checksum_sha256": "abc123",
        }
    )

    with patch.dict("os.environ", {"HERMES_HOME": str(hermes_home)}, clear=False):
        connect_team_cloud("http://localhost:8780", print_fn=lambda _: None)
        login_team_cloud(
            org_id="hermes-labs",
            user_id="alice",
            password="secret-password",
            client=FakeTeamCloudClient(),
            print_fn=lambda _: None,
        )
        save_env_value("HERMES_TEAM_CLOUD_SESSION_TOKEN", "session-token")
        result = save_local_soul("本地人格：回答要简短。", client=client, merge_with_llm=True)

    assert (hermes_home / "SOUL.md").read_text(encoding="utf-8") == "本地人格：回答要简短。"
    assert result["saved"] is True
    assert result["merge"]["status"] == "failed"
    assert result["merge"]["error_code"] == "model_provider_unavailable"
    assert "团队父人格" in result["effective_soul"]["content"]


def test_save_local_soul_uses_configured_llm_for_team_merge(tmp_path):
    from hermes_cli.config import save_env_value
    from hermes_cli.team_cloud import connect_team_cloud, login_team_cloud
    from hermes_cli.team_soul import save_local_soul
    from tests.hermes_cli.test_team_cloud_cli import FakeTeamCloudClient

    hermes_home = tmp_path / ".hermes"
    client = FakeTeamSoulClient(
        {
            "org_id": "hermes-labs",
            "team_id": "hermes-labs",
            "content": "团队父人格：必须说明我们是闻川网络科技公司。",
            "version": 1,
            "checksum_sha256": "abc123",
        }
    )
    llm_response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content="合并后人格：必须说明我们是闻川网络科技公司，同时回答要简短。")
            )
        ]
    )
    calls = []

    def fake_call_llm(**kwargs):
        calls.append(kwargs)
        return llm_response

    config = {
        "model": {"provider": "openrouter", "model": "openai/gpt-test"},
        "team_cloud": {
            "enabled": True,
            "url": "http://localhost:8780",
            "default_org_id": "hermes-labs",
            "default_team_id": "hermes-labs",
            "default_member_id": "hermes-labs:alice",
        },
    }
    with patch.dict("os.environ", {"HERMES_HOME": str(hermes_home)}, clear=False):
        connect_team_cloud("http://localhost:8780", print_fn=lambda _: None)
        login_team_cloud(
            org_id="hermes-labs",
            user_id="alice",
            password="secret-password",
            client=FakeTeamCloudClient(),
            print_fn=lambda _: None,
        )
        save_env_value("HERMES_TEAM_CLOUD_SESSION_TOKEN", "session-token")
        with patch("agent.auxiliary_client.call_llm", side_effect=fake_call_llm):
            result = save_local_soul("本地人格：回答要简短。", client=client, config=config, merge_with_llm=True)

    assert len(calls) == 1
    assert calls[0]["task"] == "team_soul_merge"
    assert calls[0]["provider"] == "openrouter"
    assert calls[0]["model"] == "openai/gpt-test"
    assert result["merge"]["status"] == "ok"
    assert result["effective_soul"]["merge_status"] == "llm"
    assert result["effective_soul"]["content"] == "合并后人格：必须说明我们是闻川网络科技公司，同时回答要简短。"


def test_soul_slash_command_is_registered():
    from hermes_cli.commands import resolve_command

    command = resolve_command("soul")
    assert command is not None
    assert command.name == "soul"
    assert command.cli_only is True
