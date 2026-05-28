from __future__ import annotations

from agent.team_tool_policy import TeamToolPolicyHook


class FakeAuthzClient:
    def __init__(self, allowed: bool):
        self.allowed = allowed
        self.calls = []

    def check_permission(self, payload):
        self.calls.append(payload)
        return {"allowed": self.allowed}


def test_team_tool_policy_allows_when_authz_allows():
    client = FakeAuthzClient(True)
    hook = TeamToolPolicyHook(authz_client=client)

    result = hook.pre_tool_call(
        tool_name="terminal",
        args={"cmd": "pwd"},
        team_context={"org_id": "org-1", "member_id": "org-1:alice"},
    )

    assert result is None
    assert client.calls == [
        {
            "org_id": "org-1",
            "resource_type": "organization",
            "resource_id": "org-1",
            "permission": "terminal_execute",
            "subject_type": "member",
            "subject_id": "org-1:alice",
        }
    ]


def test_team_tool_policy_blocks_when_authz_denies():
    hook = TeamToolPolicyHook(authz_client=FakeAuthzClient(False))

    result = hook.pre_tool_call(
        tool_name="terminal",
        args={"cmd": "pwd"},
        team_context={"org_id": "org-1", "member_id": "org-1:alice"},
    )

    assert result == {"action": "block", "message": "permission_denied"}


def test_team_tool_policy_fails_closed_without_actor_or_client():
    missing_actor = TeamToolPolicyHook(authz_client=FakeAuthzClient(True)).pre_tool_call(
        tool_name="terminal",
        args={"cmd": "pwd"},
        team_context={"org_id": "org-1"},
    )
    missing_client = TeamToolPolicyHook(authz_client=None).pre_tool_call(
        tool_name="terminal",
        args={"cmd": "pwd"},
        team_context={"org_id": "org-1", "member_id": "org-1:alice"},
    )

    assert missing_actor == {"action": "block", "message": "team_actor_missing"}
    assert missing_client == {"action": "block", "message": "authorization_unavailable"}
