from __future__ import annotations

import io
import json

import pytest
from pydantic import SecretStr, ValidationError


def test_team_cloud_package_exports_version():
    import team_cloud

    assert team_cloud.__version__


def test_config_precedence_env_then_yaml_then_secret_file_then_defaults(
    team_cloud_config,
):
    assert team_cloud_config.api_port == 8780
    assert team_cloud_config.environment == "yaml-env"
    assert team_cloud_config.database_url.get_secret_value() == "postgresql://env/db"
    assert team_cloud_config.oidc_client_secret.get_secret_value() == "yaml-client-secret"
    assert team_cloud_config.bind_host == "127.0.0.1"


def test_config_safe_dump_redacts_secrets(team_cloud_config):
    safe_dump = team_cloud_config.safe_dump()

    assert safe_dump["database_url"] == "********"
    assert safe_dump["oidc_client_secret"] == "********"
    assert "postgresql://env/db" not in json.dumps(safe_dump)
    assert "yaml-client-secret" not in json.dumps(safe_dump)


def test_request_context_validates_actor_type_and_headers():
    from team_cloud.context import RequestContext

    context = RequestContext.from_headers(
        {
            "x-request-id": "req-123",
            "x-hermes-org-id": "org-1",
            "x-hermes-member-id": "member-1",
            "x-hermes-actor-type": "service_account",
        }
    )

    assert context.request_id == "req-123"
    assert context.org_id == "org-1"
    assert context.member_id == "member-1"
    assert context.actor_type == "service_account"

    with pytest.raises(ValidationError):
        RequestContext(
            request_id="req-bad",
            org_id="org-1",
            member_id="member-1",
            actor_type="robot",
        )


def test_api_health_and_readiness_endpoints(team_cloud_config):
    from fastapi.testclient import TestClient
    from team_cloud.api import create_app

    client = TestClient(create_app(team_cloud_config))

    health = client.get("/healthz")
    assert health.status_code == 200
    assert health.json()["service"] == "team-cloud-api"
    assert health.json()["status"] == "ok"

    ready = client.get("/readyz")
    assert ready.status_code == 200
    assert ready.json()["service"] == "team-cloud-api"
    assert ready.json()["status"] == "ready"
    assert ready.json()["checks"]["config"] is True
    assert ready.json()["checks"]["migrations"] is True


def test_worker_app_exposes_heartbeat(team_cloud_config):
    from team_cloud.worker import TeamCloudWorker

    heartbeat = TeamCloudWorker(team_cloud_config).heartbeat()

    assert heartbeat["service"] == "team-cloud-worker"
    assert heartbeat["status"] == "ok"
    assert heartbeat["queues"] == []


def test_migration_runner_dry_run_discovers_postgres_artifact():
    from team_cloud.migrations import MigrationRunner

    dry_run = MigrationRunner.default().dry_run()

    assert dry_run["status"] == "ok"
    assert dry_run["count"] >= 1
    assert "001_schema_v0.sql" in dry_run["migrations"]


def test_structured_logging_emits_json_and_redacts_secrets(team_cloud_config):
    from team_cloud.logging import configure_logging, get_logger

    stream = io.StringIO()
    configure_logging(stream=stream)

    get_logger("team_cloud.test").info(
        "config_loaded",
        extra={
            "event": "config_loaded",
            "request_id": "req-123",
            "config": team_cloud_config.safe_dump(),
            "raw_secret": SecretStr("hidden-value"),
        },
    )

    payload = json.loads(stream.getvalue())
    assert payload["event"] == "config_loaded"
    assert payload["request_id"] == "req-123"
    assert payload["config"]["database_url"] == "********"
    assert payload["raw_secret"] == "********"
    assert "hidden-value" not in stream.getvalue()
