from __future__ import annotations


class FakePolicyAuthzClient:
    def __init__(self, *, allowed: bool = True):
        self.allowed = allowed

    def check(self, **kwargs):
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


def _audit_sink():
    from team_cloud.audit import InMemoryAuditLog
    from team_cloud.cloud_sessions import InMemoryCloudSessionRepository
    from team_cloud.tool_audit import TeamToolAuditSink

    cloud_sessions = InMemoryCloudSessionRepository()
    session = cloud_sessions.create_session(
        org_id="org-1",
        team_id="team-1",
        project_id="project-1",
        owner_member_id="alice",
        source_platform="cli",
    )
    audit_log = InMemoryAuditLog()
    return TeamToolAuditSink(
        cloud_session_repository=cloud_sessions,
        audit_log=audit_log,
    ), cloud_sessions, audit_log, session["id"]


def test_tool_audit_sink_records_approved_tool_call_and_audit_event():
    from team_cloud.tool_policy import TeamToolPolicyHook

    audit_sink, cloud_sessions, audit_log, session_id = _audit_sink()
    hook = TeamToolPolicyHook(
        authz_client=FakePolicyAuthzClient(),
        approval_callback=lambda **_: "once",
        audit_sink=audit_sink,
    )

    result = hook.pre_tool_call(
        tool_name="terminal",
        args={"command": "pytest"},
        task_id="run-1",
        session_id=session_id,
        team_context=_team_context(),
        platform="cli",
    )
    history = cloud_sessions.get_session(session_id)

    assert result is None
    assert history["tool_calls"][0]["decision"] == "approved"
    assert history["tool_calls"][0]["risk_level"] == "terminal"
    assert history["tool_calls"][0]["actor_member_id"] == "alice"
    assert history["tool_calls"][0]["input_redacted"] == {"command": "pytest"}
    assert audit_log.events[-1]["action"] == "tool.call.approved"
    assert audit_log.events[-1]["decision"] == "approved"
    assert audit_log.events[-1]["metadata"]["approval_choice"] == "once"


def test_tool_audit_sink_records_policy_denial():
    from team_cloud.tool_policy import TeamToolPolicyHook

    audit_sink, cloud_sessions, audit_log, session_id = _audit_sink()
    hook = TeamToolPolicyHook(
        authz_client=FakePolicyAuthzClient(allowed=False),
        approval_callback=lambda **_: "once",
        audit_sink=audit_sink,
    )

    result = hook.pre_tool_call(
        tool_name="terminal",
        args={"command": "pytest"},
        task_id="run-1",
        session_id=session_id,
        team_context=_team_context(),
    )
    history = cloud_sessions.get_session(session_id)

    assert result["action"] == "block"
    assert history["tool_calls"][0]["decision"] == "denied"
    assert history["tool_calls"][0]["error"] == "permission_denied"
    assert audit_log.events[-1]["action"] == "tool.call.denied"
    assert audit_log.events[-1]["metadata"]["reason"] == "permission_denied"


def test_tool_audit_redacts_secret_inputs_and_normalizes_schema_risk():
    from team_cloud.tool_audit import cloud_tool_risk_level, redact_tool_args
    from team_cloud.tool_policy import TeamToolPolicyHook

    audit_sink, cloud_sessions, audit_log, session_id = _audit_sink()
    hook = TeamToolPolicyHook(
        authz_client=FakePolicyAuthzClient(),
        approval_callback=lambda **_: "once",
        audit_sink=audit_sink,
    )

    result = hook.pre_tool_call(
        tool_name="web_search",
        args={"q": "roadmap", "api_key": "secret", "nested": {"password": "pw"}},
        task_id="run-1",
        session_id=session_id,
        team_context=_team_context(),
    )
    history = cloud_sessions.get_session(session_id)

    assert result is None
    assert history["tool_calls"][0]["risk_level"] == "destructive"
    assert history["tool_calls"][0]["input_redacted"]["api_key"] == "[REDACTED]"
    assert history["tool_calls"][0]["input_redacted"]["nested"]["password"] == "[REDACTED]"
    assert audit_log.events[-1]["metadata"]["risk_level"] == "secret"
    assert cloud_tool_risk_level("file", "file_read_execute") == "file_read"
    assert cloud_tool_risk_level("file", "file_write_execute") == "file_write"
    assert redact_tool_args({"token": "abc", "ok": "value"}) == {
        "token": "[REDACTED]",
        "ok": "value",
    }
