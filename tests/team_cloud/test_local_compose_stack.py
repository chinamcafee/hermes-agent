from __future__ import annotations

import os
from pathlib import Path

import yaml

COMPOSE_PATH = Path("deploy/team-cloud/compose.yaml")
DOCKERFILE_PATH = Path("deploy/team-cloud/team-cloud.Dockerfile")
DOCKERIGNORE_PATH = Path(".dockerignore")
ENV_EXAMPLE_PATH = Path("deploy/team-cloud/.env.example")
SECRETS_SCRIPT_PATH = Path("scripts/team-cloud-secrets.sh")
SMOKE_SCRIPT_PATH = Path("scripts/team-cloud-smoke.sh")
GADOC_PATH = Path("teamDoc/GADoc/P1-03-local-compose-stack.md")

REQUIRED_SERVICES = {
    "postgres",
    "postgres-init",
    "casdoor",
    "mailpit",
    "spicedb",
    "spicedb-schema-load",
    "minio",
    "minio-init",
    "team-api",
    "team-worker",
    "team-web",
    "hermes-runtime",
}

REQUIRED_NETWORKS = {"team-edge", "team-control", "team-data"}
REQUIRED_VOLUMES = {
    "team_postgres_data",
    "team_minio_data",
    "team_casdoor_conf",
    "team_spicedb_cache",
    "team_runtime_home",
}
REQUIRED_SECRETS = {
    "team_cloud_database_url",
    "team_cloud_casdoor_client_secret",
    "team_cloud_spicedb_preshared_key",
    "team_cloud_minio_secret_key",
    "team_cloud_encryption_key",
    "team_cloud_postgres_password",
    "team_cloud_casdoor_db_password",
    "team_cloud_spicedb_db_password",
    "team_cloud_minio_root_password",
}

EXPECTED_PORTS = {
    "team-web": "8781:3000",
    "team-api": "8780:8780",
    "casdoor": "18000:8000",
    "spicedb": "50051:50051",
    "spicedb-metrics": "9091:9090",
    "postgres": "54329:5432",
    "minio": "19000:9000",
    "minio-console": "19001:9001",
    "mailpit": "18025:8025",
    "mailpit-smtp": "11025:1025",
}

TEAM_API_FILE_ENVS = {
    "TEAM_CLOUD_DATABASE_URL_FILE": "/run/secrets/team_cloud_database_url",
    "TEAM_CLOUD_CASDOOR_CLIENT_SECRET_FILE": (
        "/run/secrets/team_cloud_casdoor_client_secret"
    ),
    "TEAM_CLOUD_SPICEDB_PRESHARED_KEY_FILE": (
        "/run/secrets/team_cloud_spicedb_preshared_key"
    ),
    "TEAM_CLOUD_MINIO_SECRET_KEY_FILE": "/run/secrets/team_cloud_minio_secret_key",
    "TEAM_CLOUD_ENCRYPTION_KEY_FILE": "/run/secrets/team_cloud_encryption_key",
}

EXPECTED_IMAGE_OVERRIDES = {
    "postgres": ("POSTGRES_IMAGE", "pgvector/pgvector:0.8.2-pg18-trixie"),
    "postgres-init": ("POSTGRES_IMAGE", "pgvector/pgvector:0.8.2-pg18-trixie"),
    "casdoor-init": ("ALPINE_IMAGE", "alpine:3.22.2"),
    "casdoor": ("CASDOOR_IMAGE", "casbin/casdoor:3.60.1"),
    "mailpit": ("MAILPIT_IMAGE", "axllent/mailpit:v1.29.5"),
    "spicedb-migrate": ("SPICEDB_IMAGE", "ghcr.io/authzed/spicedb:v1.53.0-debug"),
    "spicedb": ("SPICEDB_IMAGE", "ghcr.io/authzed/spicedb:v1.53.0-debug"),
    "spicedb-schema-load": ("ZED_IMAGE", "ghcr.io/authzed/zed:v1.1.1-debug"),
    "minio": ("MINIO_IMAGE", "minio/minio:RELEASE.2025-09-07T16-13-09Z"),
    "minio-init": ("MINIO_MC_IMAGE", "minio/mc:RELEASE.2025-08-13T08-35-41Z"),
    "team-api": ("TEAM_API_IMAGE", "hermes-team-api:dev"),
    "team-worker": ("TEAM_WORKER_IMAGE", "hermes-team-worker:dev"),
    "team-web": ("TEAM_WEB_IMAGE", "nginx:1.29.3-alpine"),
    "team-migrate": ("POSTGRES_IMAGE", "pgvector/pgvector:0.8.2-pg18-trixie"),
    "hermes-runtime": ("HERMES_RUNTIME_IMAGE", "hermes-team-runtime:dev"),
}

APPLICATION_BUILD_SERVICES = {"team-api", "team-worker", "hermes-runtime"}


def _load_compose() -> dict:
    assert COMPOSE_PATH.exists()
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


def test_compose_defines_required_services_networks_volumes_and_secrets():
    compose = _load_compose()

    assert REQUIRED_SERVICES <= set(compose["services"])
    assert REQUIRED_NETWORKS <= set(compose["networks"])
    assert REQUIRED_VOLUMES <= set(compose["volumes"])
    assert REQUIRED_SECRETS <= set(compose["secrets"])


def test_compose_ports_match_p0_topology():
    services = _load_compose()["services"]

    for service_name, expected_port in EXPECTED_PORTS.items():
        if service_name == "spicedb-metrics":
            ports = services["spicedb"].get("ports", [])
        elif service_name == "minio-console":
            ports = services["minio"].get("ports", [])
        elif service_name == "mailpit-smtp":
            ports = services["mailpit"].get("ports", [])
        else:
            ports = services[service_name].get("ports", [])
        assert expected_port in ports


def test_compose_network_membership_matches_topology():
    services = _load_compose()["services"]

    assert services["postgres"]["networks"] == ["team-data"]
    assert "team-edge" not in services["postgres"]["networks"]
    assert set(services["team-api"]["networks"]) == {
        "team-edge",
        "team-control",
        "team-data",
    }
    assert set(services["casdoor"]["networks"]) == {
        "team-edge",
        "team-control",
        "team-data",
    }
    assert set(services["team-worker"]["networks"]) == {"team-control", "team-data"}
    assert set(services["hermes-runtime"]["networks"]) == {"team-control"}
    assert "spicedb" not in services["hermes-runtime"].get("depends_on", {})


def test_postgres_volume_uses_pg18_compatible_mount_root():
    services = _load_compose()["services"]
    volumes = services["postgres"].get("volumes", [])

    assert "team_postgres_data:/var/lib/postgresql" in volumes
    assert "team_postgres_data:/var/lib/postgresql/data" not in volumes


def test_spicedb_schema_load_does_not_prompt_for_zed_keyring():
    services = _load_compose()["services"]
    command = "\n".join(services["spicedb-schema-load"]["entrypoint"])

    assert "zed context set" not in command
    assert "zed schema write" in command
    assert "--endpoint spicedb:50051" in command
    assert "--token" in command


def test_team_api_and_worker_use_file_secret_environment():
    services = _load_compose()["services"]

    for service_name in ("team-api", "team-worker"):
        environment = _service_environment(services[service_name])
        for env_name, expected_value in TEAM_API_FILE_ENVS.items():
            assert environment[env_name] == expected_value

        assert "TEAM_CLOUD_DATABASE_URL" not in environment
        assert "TEAM_CLOUD_CASDOOR_CLIENT_SECRET" not in environment
        assert "TEAM_CLOUD_SPICEDB_PRESHARED_KEY" not in environment
        assert "TEAM_CLOUD_MINIO_SECRET_KEY" not in environment


def test_images_are_version_pinned_and_not_latest():
    services = _load_compose()["services"]

    for service in services.values():
        image = service.get("image")
        if not image:
            continue
        assert ":latest" not in image
        assert ":" in image


def test_compose_all_images_can_be_overridden_for_registry_limited_smoke():
    services = _load_compose()["services"]

    for service_name, (env_name, default_ref) in EXPECTED_IMAGE_OVERRIDES.items():
        image = services[service_name]["image"]
        assert image == f"${{{env_name}:-{default_ref}}}", service_name


def test_team_cloud_builds_allow_python_base_image_override():
    compose = _load_compose()
    dockerfile = DOCKERFILE_PATH.read_text(encoding="utf-8")

    assert "ARG TEAM_CLOUD_PYTHON_BASE_IMAGE=python:3.13-slim-bookworm" in dockerfile
    assert "FROM ${TEAM_CLOUD_PYTHON_BASE_IMAGE}" in dockerfile

    for service_name in APPLICATION_BUILD_SERVICES:
        build = compose["services"][service_name]["build"]
        assert build["args"]["TEAM_CLOUD_PYTHON_BASE_IMAGE"] == (
            "${TEAM_CLOUD_PYTHON_BASE_IMAGE:-python:3.13-slim-bookworm}"
        )


def test_team_cloud_build_context_includes_package_readme_metadata():
    dockerfile = DOCKERFILE_PATH.read_text(encoding="utf-8")
    dockerignore = DOCKERIGNORE_PATH.read_text(encoding="utf-8")

    assert "COPY README.md pyproject.toml /app/" in dockerfile
    assert "!README.md" in dockerignore


def test_env_example_and_scripts_are_safe_and_present():
    env_example = ENV_EXAMPLE_PATH.read_text(encoding="utf-8")

    assert "postgresql://" not in env_example
    assert "client-secret" not in env_example
    assert "TEAM_CLOUD_DATABASE_URL_FILE=./secrets/" in env_example
    assert "TEAM_CLOUD_CASDOOR_CLIENT_SECRET_FILE=./secrets/" in env_example
    assert SECRETS_SCRIPT_PATH.exists()
    assert os.access(SECRETS_SCRIPT_PATH, os.X_OK)
    assert SMOKE_SCRIPT_PATH.exists()
    assert os.access(SMOKE_SCRIPT_PATH, os.X_OK)


def test_gadoc_references_compose_and_smoke_artifacts():
    doc = GADOC_PATH.read_text(encoding="utf-8")

    assert "deploy/team-cloud/compose.yaml" in doc
    assert "scripts/team-cloud-secrets.sh" in doc
    assert "scripts/team-cloud-smoke.sh" in doc
