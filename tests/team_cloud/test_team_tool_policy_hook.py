from __future__ import annotations

from pathlib import Path


class FakePolicyAuthzClient:
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
            permission=kwargs["permission"],
        )


def _team_context(**overrides):
    context = {
        "org_id": "org-1",
        "team_id": "team-1",
        "project_id": "project-1",
        "member_id": "alice",
    }
    context.update(overrides)
    return context


def test_team_tool_policy_hook_allows_after_spicedb_check():
    from team_cloud.tool_policy import TeamToolPolicyHook

    authz = FakePolicyAuthzClient()
    approvals = []

    def approve_once(**kwargs):
        approvals.append(kwargs)
        return "once"

    hook = TeamToolPolicyHook(authz_client=authz, approval_callback=approve_once)

    result = hook.pre_tool_call(
        tool_name="terminal",
        args={"command": "pytest"},
        session_id="session-1",
        tool_call_id="call-1",
        team_context=_team_context(),
        platform="cli",
    )

    assert result is None
    assert authz.calls[-1]["subject"].as_spicedb() == "user:alice"
    assert authz.calls[-1]["resource"].as_spicedb() == "tool:terminal"
    assert authz.calls[-1]["permission"] == "terminal_execute"
    assert authz.calls[-1]["consistency"] == "fully_consistent_for_sensitive"
    assert approvals[-1]["tool_name"] == "terminal"
    assert approvals[-1]["risk_level"] == "terminal"


def test_team_tool_policy_hook_blocks_denied_and_spicedb_errors():
    from team_cloud.tool_policy import TeamToolPolicyHook

    denied = TeamToolPolicyHook(authz_client=FakePolicyAuthzClient(allowed=False))
    denied_result = denied.pre_tool_call(
        tool_name="terminal",
        args={"command": "pytest"},
        team_context=_team_context(),
    )

    assert denied_result["action"] == "block"
    assert "permission_denied" in denied_result["message"]
    assert denied_result["metadata"]["risk_level"] == "terminal"

    failing = TeamToolPolicyHook(authz_client=FakePolicyAuthzClient(fail=True))
    failing_result = failing.pre_tool_call(
        tool_name="web_search",
        args={"q": "release notes"},
        team_context=_team_context(),
    )

    assert failing_result["action"] == "block"
    assert "authorization_unavailable" in failing_result["message"]
    assert failing_result["metadata"]["risk_level"] == "network"


def test_team_tool_policy_hook_fails_closed_without_team_actor_context():
    from team_cloud.tool_policy import TeamToolPolicyHook

    hook = TeamToolPolicyHook(authz_client=FakePolicyAuthzClient())

    result = hook.pre_tool_call(
        tool_name="read_file",
        args={"path": "README.md"},
        team_context={"org_id": "org-1"},
    )

    assert result["action"] == "block"
    assert "team_actor_missing" in result["message"]


def test_team_tool_policy_hook_blocks_high_risk_approval_deny_timeout_and_missing_gate():
    from team_cloud.tool_policy import TeamToolPolicyHook

    denied = TeamToolPolicyHook(
        authz_client=FakePolicyAuthzClient(),
        approval_callback=lambda **_: "deny",
    )
    denied_result = denied.pre_tool_call(
        tool_name="terminal",
        args={"command": "pytest"},
        team_context=_team_context(),
    )

    assert denied_result["action"] == "block"
    assert "approval_denied" in denied_result["message"]
    assert denied_result["metadata"]["approval_choice"] == "deny"

    timed_out = TeamToolPolicyHook(
        authz_client=FakePolicyAuthzClient(),
        approval_callback=lambda **_: "timeout",
    )
    timeout_result = timed_out.pre_tool_call(
        tool_name="terminal",
        args={"command": "pytest"},
        team_context=_team_context(),
    )

    assert timeout_result["action"] == "block"
    assert "approval_timeout" in timeout_result["message"]
    assert timeout_result["metadata"]["approval_choice"] == "timeout"

    missing_gate = TeamToolPolicyHook(authz_client=FakePolicyAuthzClient())
    missing_result = missing_gate.pre_tool_call(
        tool_name="terminal",
        args={"command": "pytest"},
        team_context=_team_context(),
    )

    assert missing_result["action"] == "block"
    assert "approval_unavailable" in missing_result["message"]


def test_team_tool_policy_hook_skips_approval_for_low_risk_tools():
    from team_cloud.tool_policy import TeamToolPolicyHook

    approvals = []

    hook = TeamToolPolicyHook(
        authz_client=FakePolicyAuthzClient(),
        approval_callback=lambda **kwargs: approvals.append(kwargs) or "deny",
    )

    result = hook.pre_tool_call(
        tool_name="web_search",
        args={"q": "release notes"},
        team_context=_team_context(),
    )

    assert result is None
    assert approvals == []


def test_pre_tool_call_helper_forwards_team_policy_context(monkeypatch):
    from hermes_cli.plugins import get_pre_tool_call_block_message

    captured = {}

    def fake_invoke_hook(hook_name, **kwargs):
        captured["hook_name"] = hook_name
        captured["kwargs"] = kwargs
        return []

    monkeypatch.setattr("hermes_cli.plugins.invoke_hook", fake_invoke_hook)

    assert (
        get_pre_tool_call_block_message(
            "terminal",
            {"command": "pytest"},
            task_id="task-1",
            session_id="session-1",
            tool_call_id="call-1",
            team_context=_team_context(),
            platform="cli",
            user_id="alice-local",
        )
        is None
    )
    assert captured["hook_name"] == "pre_tool_call"
    assert captured["kwargs"]["team_context"]["member_id"] == "alice"
    assert captured["kwargs"]["platform"] == "cli"
    assert captured["kwargs"]["user_id"] == "alice-local"


def test_agent_pre_tool_call_context_helper_includes_team_identity():
    from agent.tool_dispatch_helpers import build_pre_tool_call_hook_kwargs

    class Agent:
        session_id = "session-1"
        team_context = _team_context()
        platform = "telegram"
        _user_id = "telegram-user-42"

    kwargs = build_pre_tool_call_hook_kwargs(
        Agent(),
        task_id="task-1",
        tool_call_id="call-1",
    )

    assert kwargs["task_id"] == "task-1"
    assert kwargs["session_id"] == "session-1"
    assert kwargs["tool_call_id"] == "call-1"
    assert kwargs["team_context"]["member_id"] == "alice"
    assert kwargs["platform"] == "telegram"
    assert kwargs["user_id"] == "telegram-user-42"


def test_team_policy_plugin_registers_pre_tool_call_hook():
    manifest = Path("plugins/team_policy/plugin.yaml").read_text(encoding="utf-8")
    init = Path("plugins/team_policy/__init__.py").read_text(encoding="utf-8")

    assert "pre_tool_call" in manifest
    assert "TeamToolPolicyHook" in init
    assert "HERMES_TEAM_TOOL_POLICY_ENABLED" in init
