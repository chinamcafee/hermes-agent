from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from gateway.config import PlatformConfig
from gateway.platforms.api_server import (
    APIServerAdapter,
    security_headers_middleware,
)


def _make_adapter(
    *,
    api_key: str = "sk-secret",
    team_cloud_service_token: str | None = None,
) -> APIServerAdapter:
    extra = {"key": api_key}
    if team_cloud_service_token is not None:
        extra["team_cloud_service_token"] = team_cloud_service_token
    return APIServerAdapter(PlatformConfig(enabled=True, extra=extra))


def _create_app(adapter: APIServerAdapter) -> web.Application:
    middlewares = [mw for mw in (security_headers_middleware,) if mw is not None]
    app = web.Application(middlewares=middlewares)
    app["api_server_adapter"] = adapter
    app.router.add_post("/v1/chat/completions", adapter._handle_chat_completions)
    app.router.add_get("/v1/capabilities", adapter._handle_capabilities)
    return app


def _team_headers(*, token: str = "team-token") -> dict[str, str]:
    return {
        "Authorization": "Bearer sk-secret",
        "X-Hermes-Team-Cloud-Token": token,
        "X-Hermes-Org-Id": "org-1",
        "X-Hermes-Team-Id": "team-1",
        "X-Hermes-Project-Id": "project-1",
        "X-Hermes-Member-Id": "alice",
    }


@pytest.mark.asyncio
async def test_team_identity_headers_require_configured_service_token():
    adapter = _make_adapter()
    app = _create_app(adapter)

    async with TestClient(TestServer(app)) as cli:
        with patch.object(adapter, "_run_agent", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = (
                {"final_response": "ignored", "messages": [], "api_calls": 1},
                {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
            )
            response = await cli.post(
                "/v1/chat/completions",
                headers=_team_headers(),
                json={
                    "model": "hermes-agent",
                    "messages": [{"role": "user", "content": "hi"}],
                },
            )

    assert response.status == 403
    mock_run.assert_not_called()


@pytest.mark.asyncio
async def test_team_identity_headers_pass_team_context_to_chat_agent():
    adapter = _make_adapter(team_cloud_service_token="team-token")
    app = _create_app(adapter)

    async with TestClient(TestServer(app)) as cli:
        with patch.object(adapter, "_run_agent", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = (
                {"final_response": "ok", "messages": [], "api_calls": 1},
                {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
            )
            response = await cli.post(
                "/v1/chat/completions",
                headers=_team_headers(),
                json={
                    "model": "hermes-agent",
                    "messages": [{"role": "user", "content": "hi"}],
                },
            )

    assert response.status == 200
    assert mock_run.call_args.kwargs["team_context"] == {
        "org_id": "org-1",
        "team_id": "team-1",
        "project_id": "project-1",
        "member_id": "alice",
    }


@pytest.mark.asyncio
async def test_team_identity_headers_reject_invalid_service_token():
    adapter = _make_adapter(team_cloud_service_token="team-token")
    app = _create_app(adapter)

    async with TestClient(TestServer(app)) as cli:
        with patch.object(adapter, "_run_agent", new_callable=AsyncMock) as mock_run:
            response = await cli.post(
                "/v1/chat/completions",
                headers=_team_headers(token="wrong-token"),
                json={
                    "model": "hermes-agent",
                    "messages": [{"role": "user", "content": "hi"}],
                },
            )

    assert response.status == 401
    mock_run.assert_not_called()


def test_create_agent_receives_team_context_from_api_server():
    adapter = _make_adapter(team_cloud_service_token="team-token")
    captured_kwargs = {}

    def fake_agent(**kwargs):
        captured_kwargs.update(kwargs)
        return MagicMock()

    team_context = {
        "org_id": "org-1",
        "team_id": "team-1",
        "project_id": "project-1",
        "member_id": "alice",
    }

    with (
        patch("gateway.run._resolve_runtime_agent_kwargs", return_value={}),
        patch("gateway.run._resolve_gateway_model", return_value="hermes-agent"),
        patch("gateway.run._load_gateway_config", return_value={}),
        patch("gateway.run.GatewayRunner._load_reasoning_config", return_value=None),
        patch("gateway.run.GatewayRunner._load_fallback_model", return_value=None),
        patch("hermes_cli.tools_config._get_platform_tools", return_value=set()),
        patch("run_agent.AIAgent", side_effect=fake_agent),
    ):
        adapter._create_agent(team_context=team_context)

    assert captured_kwargs["team_context"] == team_context
