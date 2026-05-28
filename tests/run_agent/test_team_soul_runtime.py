from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch


def _agent(**overrides):
    base = {
        "load_soul_identity": False,
        "skip_context_files": True,
        "valid_tool_names": set(),
        "_kanban_worker_guidance": "",
        "_tool_use_enforcement": "auto",
        "provider": "",
        "model": "",
        "platform": "cli",
        "_memory_store": None,
        "_memory_manager": None,
        "_memory_enabled": False,
        "_user_profile_enabled": False,
        "pass_session_id": False,
        "session_id": "",
        "team_context": None,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_system_prompt_uses_effective_team_soul_when_in_team_mode():
    from agent.system_prompt import build_system_prompt_parts

    agent = _agent(load_soul_identity=True, team_context={"org_id": "org-1", "team_id": "org-1", "member_id": "org-1:alice"})
    with (
        patch("run_agent.build_nous_subscription_prompt", return_value=""),
        patch("run_agent.build_environment_hints", return_value=""),
        patch("hermes_cli.team_soul.effective_soul_for_runtime", return_value="团队父人格 + 本地人格合并结果"),
        patch("run_agent.load_soul_md", return_value="本地人格原文"),
    ):
        parts = build_system_prompt_parts(agent)

    assert "团队父人格 + 本地人格合并结果" in parts["stable"]
    assert "本地人格原文" not in parts["stable"]


def test_system_prompt_keeps_local_soul_outside_team_mode():
    from agent.system_prompt import build_system_prompt_parts

    agent = _agent(load_soul_identity=True, team_context=None)
    with (
        patch("run_agent.build_nous_subscription_prompt", return_value=""),
        patch("run_agent.build_environment_hints", return_value=""),
        patch("hermes_cli.team_soul.effective_soul_for_runtime", return_value="团队父人格 + 本地人格合并结果"),
        patch("run_agent.load_soul_md", return_value="本地人格原文"),
    ):
        parts = build_system_prompt_parts(agent)

    assert "本地人格原文" in parts["stable"]
    assert "团队父人格 + 本地人格合并结果" not in parts["stable"]
