from __future__ import annotations

from pathlib import Path

import yaml


COMPOSE_PATH = Path("deploy/team-cloud/compose.yaml")
ENV_EXAMPLE_PATH = Path("deploy/team-cloud/.env.example")
DOC_PATH = Path("teamDoc/GADoc/P4-01-compose-hardening.md")
FOUNDATION_SMOKE = Path("scripts/team-cloud-foundation-smoke.sh")

LONG_RUNNING_SERVICES = {
    "postgres",
    "casdoor",
    "mailpit",
    "spicedb",
    "minio",
    "team-api",
    "team-worker",
    "team-web",
    "hermes-runtime",
}


def _load_compose() -> dict:
    return yaml.safe_load(COMPOSE_PATH.read_text(encoding="utf-8"))


def _service_environment(service: dict) -> dict[str, str]:
    environment = service.get("environment", {})
    if isinstance(environment, dict):
        return {str(key): str(value) for key, value in environment.items()}
    result: dict[str, str] = {}
    for item in environment:
        key, _, value = str(item).partition("=")
        result[key] = value
    return result


def _volume_targets(service: dict) -> set[str]:
    targets: set[str] = set()
    for volume in service.get("volumes", []):
        if isinstance(volume, str):
            parts = volume.split(":")
            if len(parts) >= 2:
                targets.add(parts[1])
        elif isinstance(volume, dict):
            targets.add(str(volume.get("target", "")))
    return targets


def test_compose_hardening_adds_healthchecks_to_all_long_running_services():
    services = _load_compose()["services"]

    for service_name in LONG_RUNNING_SERVICES:
        healthcheck = services[service_name].get("healthcheck")
        assert healthcheck, service_name
        assert healthcheck.get("test"), service_name
        assert healthcheck.get("interval"), service_name
        assert healthcheck.get("timeout"), service_name
        assert healthcheck.get("retries"), service_name

    spicedb_health = " ".join(services["spicedb"]["healthcheck"]["test"])
    team_web_health = " ".join(services["team-web"]["healthcheck"]["test"])
    assert "nc -z" not in spicedb_health
    assert "spicedb version" in spicedb_health
    assert "127.0.0.1:3000" in team_web_health


def test_compose_hardening_fixes_backup_and_tls_mount_contracts():
    services = _load_compose()["services"]

    assert "./backups:/backups" in services["postgres"].get("volumes", [])
    assert "./backups:/backups" in services["minio"].get("volumes", [])
    assert "./backups:/backups" in services["team-api"].get("volumes", [])

    for service_name in ("team-api", "team-web"):
        assert "/etc/hermes-team-cloud/tls" in _volume_targets(services[service_name])

    team_api_env = _service_environment(services["team-api"])
    assert team_api_env["TEAM_CLOUD_TLS_CERT_FILE"] == (
        "/etc/hermes-team-cloud/tls/dev-cert.pem"
    )
    assert team_api_env["TEAM_CLOUD_TLS_KEY_FILE"] == (
        "/etc/hermes-team-cloud/tls/dev-key.pem"
    )


def test_compose_hardening_documents_env_and_smoke_coverage():
    env_example = ENV_EXAMPLE_PATH.read_text(encoding="utf-8")
    smoke = FOUNDATION_SMOKE.read_text(encoding="utf-8")
    doc = DOC_PATH.read_text(encoding="utf-8")

    assert "TEAM_CLOUD_TLS_CERT_FILE=./certs/dev/dev-cert.pem" in env_example
    assert "TEAM_CLOUD_TLS_KEY_FILE=./certs/dev/dev-key.pem" in env_example
    assert "tests/team_cloud/test_compose_hardening.py" in smoke
    assert "healthcheck" in doc
    assert "backup mount" in doc
    assert "dev TLS" in doc
