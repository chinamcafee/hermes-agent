from __future__ import annotations

import sys
import threading
import types
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

import gateway.run as gateway_run
from gateway.config import GatewayConfig, Platform, PlatformConfig
from gateway.platforms.base import MessageEvent
from gateway.session import SessionSource, build_session_key


class _StaticTeamIdentityResolver:
    def __init__(self, result):
        self.result = result
        self.calls = []

    async def resolve(self, source, *, shared_session: bool):
        self.calls.append((source, shared_session))
        return self.result


class _CapturingAgent:
    last_init = None

    def __init__(self, *args, **kwargs):
        type(self).last_init = dict(kwargs)
        self.tools = []

    def run_conversation(self, user_message, conversation_history=None, task_id=None, persist_user_message=None):
        return {
            "final_response": "ok",
            "messages": [],
            "api_calls": 1,
            "completed": True,
        }


def _install_fake_agent(monkeypatch):
    fake_run_agent = types.ModuleType("run_agent")
    fake_run_agent.AIAgent = _CapturingAgent
    monkeypatch.setitem(sys.modules, "run_agent", fake_run_agent)


def _make_source(*, chat_type: str = "dm", thread_id: str | None = None) -> SessionSource:
    return SessionSource(
        platform=Platform.TELEGRAM,
        chat_id="chat-1",
        chat_type=chat_type,
        user_id="tg-alice",
        user_name="Alice",
        thread_id=thread_id,
        guild_id="workspace-1",
    )


def _make_event(text: str = "hello", *, chat_type: str = "dm") -> MessageEvent:
    return MessageEvent(
        text=text,
        source=_make_source(chat_type=chat_type),
        message_id="m1",
    )


def _make_runner(resolver) -> gateway_run.GatewayRunner:
    config = GatewayConfig(
        platforms={Platform.TELEGRAM: PlatformConfig(enabled=True)},
    )
    runner = object.__new__(gateway_run.GatewayRunner)
    runner.config = config
    runner.adapters = {Platform.TELEGRAM: SimpleNamespace(send=AsyncMock())}
    runner.pairing_store = MagicMock()
    runner.pairing_store.is_approved.return_value = False
    runner.session_store = SimpleNamespace(
        _generate_session_key=lambda source: build_session_key(
            source,
            group_sessions_per_user=config.group_sessions_per_user,
            thread_sessions_per_user=config.thread_sessions_per_user,
        )
    )
    runner._running_agents = {}
    runner._running_agents_ts = {}
    runner._session_run_generation = {}
    runner._update_prompt_pending = {}
    runner._team_identity_resolver = resolver
    return runner


@pytest.mark.asyncio
async def test_gateway_identity_resolver_prefixes_session_key_and_sets_team_context(monkeypatch):
    monkeypatch.setenv("TELEGRAM_ALLOWED_USERS", "*")
    from gateway.team_identity import GatewayTeamIdentityResolution

    team_context = {
        "org_id": "org-1",
        "team_id": "team-1",
        "project_id": "project-1",
        "member_id": "alice",
        "personal_memory_enabled": True,
    }
    resolver = _StaticTeamIdentityResolver(
        GatewayTeamIdentityResolution.resolved(team_context=team_context)
    )
    runner = _make_runner(resolver)
    captured = {}

    async def _capture(event, source, quick_key, run_generation):
        captured["team_context"] = getattr(event, "team_context", None)
        captured["quick_key"] = quick_key
        return "ok"

    runner._handle_message_with_agent = _capture  # noqa: SLF001

    result = await runner._handle_message(_make_event("hello"))

    assert result == "ok"
    assert captured["team_context"] == team_context
    assert captured["quick_key"].startswith("team:org-1:team-1:")
    assert captured["quick_key"].endswith("agent:main:telegram:dm:chat-1")
    assert resolver.calls[0][1] is False


@pytest.mark.asyncio
async def test_gateway_identity_resolver_returns_binding_prompt_without_creating_agent(monkeypatch):
    monkeypatch.setenv("TELEGRAM_ALLOWED_USERS", "*")
    from gateway.team_identity import GatewayTeamIdentityResolution

    resolver = _StaticTeamIdentityResolver(
        GatewayTeamIdentityResolution.unbound("Bind your Hermes Team Cloud account.")
    )
    runner = _make_runner(resolver)
    runner._handle_message_with_agent = AsyncMock(return_value="unexpected")  # noqa: SLF001

    result = await runner._handle_message(_make_event("hello"))

    assert result == "Bind your Hermes Team Cloud account."
    runner._handle_message_with_agent.assert_not_awaited()
    assert runner._running_agents == {}


def test_prefixed_team_session_key_remains_parseable_for_platform_routing():
    from gateway.run import _parse_session_key
    from gateway.team_identity import prefix_session_key_for_team

    source = _make_source()
    prefixed = prefix_session_key_for_team(
        build_session_key(source),
        {"org_id": "org-1", "team_id": "team:platform"},
    )

    assert prefixed == "team:org-1:team%3Aplatform:agent:main:telegram:dm:chat-1"
    assert _parse_session_key(prefixed) == {
        "platform": "telegram",
        "chat_type": "dm",
        "chat_id": "chat-1",
    }


@pytest.mark.asyncio
async def test_run_agent_passes_team_context_to_aiagent(monkeypatch, tmp_path):
    _install_fake_agent(monkeypatch)
    runner = object.__new__(gateway_run.GatewayRunner)
    runner.adapters = {}
    runner._ephemeral_system_prompt = ""
    runner._prefill_messages = []
    runner._reasoning_config = None
    runner._service_tier = None
    runner._provider_routing = {}
    runner._fallback_model = None
    runner._running_agents = {}
    runner._pending_model_notes = {}
    runner._session_db = None
    runner._agent_cache = {}
    runner._agent_cache_lock = threading.Lock()
    runner._session_model_overrides = {}
    runner._session_reasoning_overrides = {}
    runner.hooks = SimpleNamespace(loaded_hooks=False)
    runner.config = SimpleNamespace(streaming=None)
    runner.session_store = SimpleNamespace(
        get_or_create_session=lambda source: SimpleNamespace(session_id="session-1"),
        load_transcript=lambda session_id: [],
    )

    monkeypatch.setattr(gateway_run, "_hermes_home", tmp_path)
    monkeypatch.setattr(gateway_run, "_env_path", tmp_path / ".env")
    monkeypatch.setattr(gateway_run, "load_dotenv", lambda *args, **kwargs: None)
    monkeypatch.setattr(gateway_run, "_load_gateway_config", lambda: {})
    monkeypatch.setattr(gateway_run, "_resolve_gateway_model", lambda config=None: "gpt-5.4")
    monkeypatch.setattr(
        gateway_run,
        "_resolve_runtime_agent_kwargs",
        lambda: {
            "provider": "openrouter",
            "api_mode": "chat_completions",
            "base_url": "https://openrouter.ai/api/v1",
            "api_key": "***",
        },
    )

    import hermes_cli.tools_config as tools_config

    monkeypatch.setattr(tools_config, "_get_platform_tools", lambda user_config, platform_key: {"core"})

    team_context = {
        "org_id": "org-1",
        "team_id": "team-1",
        "member_id": "alice",
    }
    result = await runner._run_agent(
        message="hi",
        context_prompt="",
        history=[],
        source=_make_source(),
        session_id="session-1",
        session_key="team:org-1:team-1:agent:main:telegram:dm:chat-1",
        team_context=team_context,
    )

    assert result["final_response"] == "ok"
    assert _CapturingAgent.last_init["team_context"] == team_context
