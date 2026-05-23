"""Configuration and secret loading for Team Cloud."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

_SECRET_FIELDS = {
    "database_url",
    "casdoor_client_secret",
    "spicedb_preshared_key",
    "minio_secret_key",
    "encryption_key",
}

_DIRECT_ENV_TO_FIELD = {
    "TEAM_CLOUD_ENVIRONMENT": "environment",
    "TEAM_CLOUD_BIND_HOST": "bind_host",
    "TEAM_CLOUD_API_PORT": "api_port",
    "TEAM_CLOUD_LOG_LEVEL": "log_level",
    "TEAM_CLOUD_JWT_ISSUER": "jwt_issuer",
    "TEAM_CLOUD_CASDOOR_BASE_URL": "casdoor_base_url",
    "TEAM_CLOUD_CASDOOR_CLIENT_ID": "casdoor_client_id",
    "TEAM_CLOUD_DATABASE_URL": "database_url",
    "TEAM_CLOUD_CASDOOR_CLIENT_SECRET": "casdoor_client_secret",
    "TEAM_CLOUD_OIDC_CLIENT_SECRET": "casdoor_client_secret",
    "TEAM_CLOUD_SPICEDB_ENDPOINT": "spicedb_endpoint",
    "TEAM_CLOUD_SPICEDB_PRESHARED_KEY": "spicedb_preshared_key",
    "TEAM_CLOUD_MINIO_ENDPOINT": "minio_endpoint",
    "TEAM_CLOUD_MINIO_ACCESS_KEY": "minio_access_key",
    "TEAM_CLOUD_MINIO_SECRET_KEY": "minio_secret_key",
    "TEAM_CLOUD_ENCRYPTION_KEY": "encryption_key",
}

_FILE_ENV_TO_FIELD = {
    "TEAM_CLOUD_DATABASE_URL_FILE": "database_url",
    "TEAM_CLOUD_CASDOOR_CLIENT_SECRET_FILE": "casdoor_client_secret",
    "TEAM_CLOUD_OIDC_CLIENT_SECRET_FILE": "casdoor_client_secret",
    "TEAM_CLOUD_SPICEDB_PRESHARED_KEY_FILE": "spicedb_preshared_key",
    "TEAM_CLOUD_MINIO_SECRET_KEY_FILE": "minio_secret_key",
    "TEAM_CLOUD_ENCRYPTION_KEY_FILE": "encryption_key",
}

_YAML_SECRET_FILE_KEYS = {
    "database_url": ("database_url_file",),
    "casdoor_client_secret": (
        "casdoor_client_secret_file",
        "oidc_client_secret_file",
    ),
    "spicedb_preshared_key": ("spicedb_preshared_key_file",),
    "minio_secret_key": ("minio_secret_key_file",),
    "encryption_key": ("encryption_key_file",),
}

_YAML_DIRECT_ALIASES = {
    "casdoor_client_secret": ("oidc_client_secret",),
}


class SecretFileError(RuntimeError):
    """Raised when a configured secret file cannot be consumed safely."""


@dataclass(frozen=True)
class EnvVarSpec:
    field_name: str
    description: str
    secret: bool = False
    file_only: bool = False
    example: str = ""


@dataclass(frozen=True)
class SecretFileStatus:
    field_name: str
    path: Path
    source: str
    exists: bool
    readable: bool


ENV_SCHEMA: dict[str, EnvVarSpec] = {
    "TEAM_CLOUD_ENVIRONMENT": EnvVarSpec(
        "environment", "Runtime environment label.", example="local"
    ),
    "TEAM_CLOUD_BIND_HOST": EnvVarSpec(
        "bind_host", "Team API bind host.", example="0.0.0.0"
    ),
    "TEAM_CLOUD_API_PORT": EnvVarSpec(
        "api_port", "Team API listen port.", example="8780"
    ),
    "TEAM_CLOUD_LOG_LEVEL": EnvVarSpec(
        "log_level", "Structured log level.", example="INFO"
    ),
    "TEAM_CLOUD_JWT_ISSUER": EnvVarSpec(
        "jwt_issuer", "Expected Casdoor issuer URL.", example="http://casdoor:8000"
    ),
    "TEAM_CLOUD_CASDOOR_BASE_URL": EnvVarSpec(
        "casdoor_base_url", "Casdoor base URL.", example="http://casdoor:8000"
    ),
    "TEAM_CLOUD_CASDOOR_CLIENT_ID": EnvVarSpec(
        "casdoor_client_id", "Casdoor Team API client ID.", example="hermes-team-api"
    ),
    "TEAM_CLOUD_SPICEDB_ENDPOINT": EnvVarSpec(
        "spicedb_endpoint", "SpiceDB gRPC endpoint.", example="spicedb:50051"
    ),
    "TEAM_CLOUD_MINIO_ENDPOINT": EnvVarSpec(
        "minio_endpoint", "MinIO S3 API endpoint.", example="http://minio:9000"
    ),
    "TEAM_CLOUD_MINIO_ACCESS_KEY": EnvVarSpec(
        "minio_access_key", "MinIO service account access key.", example="hermes_team"
    ),
    "TEAM_CLOUD_DATABASE_URL_FILE": EnvVarSpec(
        "database_url",
        "Path to the Team Cloud PostgreSQL URL secret file.",
        secret=True,
        file_only=True,
        example="./secrets/team_cloud_database_url.txt",
    ),
    "TEAM_CLOUD_CASDOOR_CLIENT_SECRET_FILE": EnvVarSpec(
        "casdoor_client_secret",
        "Path to the Casdoor client secret file.",
        secret=True,
        file_only=True,
        example="./secrets/team_cloud_casdoor_client_secret.txt",
    ),
    "TEAM_CLOUD_SPICEDB_PRESHARED_KEY_FILE": EnvVarSpec(
        "spicedb_preshared_key",
        "Path to the SpiceDB pre-shared key file.",
        secret=True,
        file_only=True,
        example="./secrets/team_cloud_spicedb_preshared_key.txt",
    ),
    "TEAM_CLOUD_MINIO_SECRET_KEY_FILE": EnvVarSpec(
        "minio_secret_key",
        "Path to the MinIO service account secret key file.",
        secret=True,
        file_only=True,
        example="./secrets/team_cloud_minio_secret_key.txt",
    ),
    "TEAM_CLOUD_ENCRYPTION_KEY_FILE": EnvVarSpec(
        "encryption_key",
        "Path to the Team Cloud envelope encryption key file.",
        secret=True,
        file_only=True,
        example="./secrets/team_cloud_encryption_key.txt",
    ),
}


class TeamCloudConfig(BaseModel):
    """Resolved Team Cloud configuration.

    Precedence is direct env > direct yaml > secret file > defaults. For secret
    files, an env-provided ``*_FILE`` path wins over a yaml ``*_file`` path.
    """

    model_config = ConfigDict(extra="forbid")

    environment: str = "local"
    bind_host: str = "127.0.0.1"
    api_port: int = 8780
    log_level: str = "INFO"
    jwt_issuer: str | None = None
    casdoor_base_url: str = "http://casdoor:8000"
    casdoor_client_id: str = "hermes-team-api"
    casdoor_client_secret: SecretStr | None = None
    database_url: SecretStr | None = None
    spicedb_endpoint: str = "spicedb:50051"
    spicedb_preshared_key: SecretStr | None = None
    minio_endpoint: str = "http://minio:9000"
    minio_access_key: str = "hermes_team"
    minio_secret_key: SecretStr | None = None
    encryption_key: SecretStr | None = None

    @property
    def oidc_client_secret(self) -> SecretStr | None:
        return self.casdoor_client_secret

    @field_validator("api_port")
    @classmethod
    def _validate_api_port(cls, value: int) -> int:
        if value < 1 or value > 65535:
            raise ValueError("api_port must be between 1 and 65535")
        return value

    def safe_dump(self) -> dict[str, Any]:
        data = self.model_dump(mode="json")
        for field_name in _SECRET_FIELDS:
            if getattr(self, field_name) is not None:
                data[field_name] = "********"
        if self.casdoor_client_secret is not None:
            data["oidc_client_secret"] = "********"
        return data


def load_config(
    config_path: str | Path | None = None,
    *,
    env: Mapping[str, str] | None = None,
) -> TeamCloudConfig:
    """Load config with env > yaml > secret file > defaults precedence."""

    env_source = os.environ if env is None else env
    yaml_data, config_dir = _load_yaml_config(config_path)
    yaml_values = _load_yaml_values(yaml_data)
    env_values = _load_env_values(env_source)
    direct_secret_fields = _direct_secret_fields(yaml_values, env_values)
    yaml_secret_values = _load_yaml_secret_values(
        yaml_data,
        config_dir,
        skip_fields=direct_secret_fields,
    )
    env_file_secret_values = _load_env_file_secret_values(
        env_source,
        skip_fields=direct_secret_fields,
    )

    merged: dict[str, Any] = {}
    merged.update(yaml_secret_values)
    merged.update(env_file_secret_values)
    merged.update(yaml_values)
    merged.update(env_values)
    return TeamCloudConfig(**merged)


def validate_secret_files(
    config_path: str | Path | None = None,
    *,
    env: Mapping[str, str] | None = None,
) -> list[SecretFileStatus]:
    env_source = os.environ if env is None else env
    yaml_data, config_dir = _load_yaml_config(config_path)
    statuses: list[SecretFileStatus] = []

    for field_name, keys in _YAML_SECRET_FILE_KEYS.items():
        for key in keys:
            file_value = yaml_data.get(key)
            if file_value:
                statuses.append(
                    _secret_file_status(
                        field_name,
                        _resolve_secret_path(file_value, config_dir),
                        f"yaml:{key}",
                    )
                )
                break

    for env_name, field_name in _FILE_ENV_TO_FIELD.items():
        file_value = env_source.get(env_name)
        if file_value:
            statuses.append(
                _secret_file_status(
                    field_name,
                    _resolve_secret_path(file_value, None),
                    f"env:{env_name}",
                )
            )

    return statuses


def render_env_example() -> str:
    lines = [
        "# Hermes Team Cloud environment example.",
        "# Secret values live in files; this file only points to paths.",
        "",
    ]
    for env_name, spec in ENV_SCHEMA.items():
        lines.append(f"# {spec.description}")
        lines.append(f"{env_name}={spec.example}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _load_yaml_config(config_path: str | Path | None) -> tuple[dict[str, Any], Path | None]:
    if config_path is None:
        return {}, None

    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Team Cloud config file not found: {path}")

    loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(loaded, dict):
        raise ValueError("Team Cloud config file must contain a mapping")
    return dict(loaded), path.parent


def _load_yaml_values(source: Mapping[str, Any]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for field_name in TeamCloudConfig.model_fields:
        if field_name in source and source[field_name] is not None:
            values[field_name] = source[field_name]

    for canonical_field, aliases in _YAML_DIRECT_ALIASES.items():
        for alias in aliases:
            if alias in source and source[alias] is not None:
                values.setdefault(canonical_field, source[alias])
                break
    return values


def _load_env_values(env: Mapping[str, str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for env_name, field_name in _DIRECT_ENV_TO_FIELD.items():
        value = env.get(env_name)
        if value not in (None, ""):
            values[field_name] = value
    return values


def _load_yaml_secret_values(
    source: Mapping[str, Any],
    config_dir: Path | None,
    *,
    skip_fields: set[str],
) -> dict[str, str]:
    values: dict[str, str] = {}
    for field_name, keys in _YAML_SECRET_FILE_KEYS.items():
        if field_name in skip_fields:
            continue
        for key in keys:
            file_value = source.get(key)
            if file_value:
                path = _resolve_secret_path(file_value, config_dir)
                values[field_name] = _read_secret_file(field_name, path, f"yaml:{key}")
                break
    return values


def _load_env_file_secret_values(
    env: Mapping[str, str],
    *,
    skip_fields: set[str],
) -> dict[str, str]:
    values: dict[str, str] = {}
    for env_name, field_name in _FILE_ENV_TO_FIELD.items():
        if field_name in skip_fields:
            continue
        file_value = env.get(env_name)
        if file_value not in (None, ""):
            path = _resolve_secret_path(file_value, None)
            values[field_name] = _read_secret_file(field_name, path, f"env:{env_name}")
    return values


def _direct_secret_fields(
    yaml_values: Mapping[str, Any],
    env_values: Mapping[str, Any],
) -> set[str]:
    direct_fields = set()
    for source in (yaml_values, env_values):
        for field_name in _SECRET_FIELDS:
            if source.get(field_name) is not None:
                direct_fields.add(field_name)
    return direct_fields


def _resolve_secret_path(file_value: Any, base_dir: Path | None) -> Path:
    path = Path(str(file_value))
    if not path.is_absolute() and base_dir is not None:
        return base_dir / path
    return path


def _secret_file_status(field_name: str, path: Path, source: str) -> SecretFileStatus:
    exists = path.exists() and path.is_file()
    readable = exists and os.access(path, os.R_OK)
    return SecretFileStatus(
        field_name=field_name,
        path=path,
        source=source,
        exists=exists,
        readable=readable,
    )


def _read_secret_file(field_name: str, path: Path, source: str) -> str:
    status = _secret_file_status(field_name, path, source)
    if not status.exists:
        raise SecretFileError(f"Secret file for {field_name} not found: {path}")
    if not status.readable:
        raise SecretFileError(f"Secret file for {field_name} is not readable: {path}")
    try:
        value = path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise SecretFileError(f"Secret file for {field_name} cannot be read: {path}") from exc
    if not value:
        raise SecretFileError(f"Secret file for {field_name} is empty: {path}")
    return value
