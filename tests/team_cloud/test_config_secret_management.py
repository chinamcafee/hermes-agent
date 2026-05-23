from __future__ import annotations

from pathlib import Path

import pytest

REQUIRED_FILE_SECRET_ENVS = {
    "TEAM_CLOUD_DATABASE_URL_FILE",
    "TEAM_CLOUD_CASDOOR_CLIENT_SECRET_FILE",
    "TEAM_CLOUD_SPICEDB_PRESHARED_KEY_FILE",
    "TEAM_CLOUD_MINIO_SECRET_KEY_FILE",
    "TEAM_CLOUD_ENCRYPTION_KEY_FILE",
}


def _write_config(path: Path, lines: list[str]) -> Path:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_env_schema_covers_file_secret_vars_and_safe_example():
    from team_cloud.config import ENV_SCHEMA, render_env_example

    for env_name in REQUIRED_FILE_SECRET_ENVS:
        assert env_name in ENV_SCHEMA
        assert ENV_SCHEMA[env_name].secret is True
        assert ENV_SCHEMA[env_name].file_only is True

    example = render_env_example()
    for env_name in REQUIRED_FILE_SECRET_ENVS:
        assert f"{env_name}=./secrets/" in example

    assert "TEAM_CLOUD_DATABASE_URL=" not in example
    assert "TEAM_CLOUD_CASDOOR_CLIENT_SECRET=" not in example
    assert "postgresql://" not in example
    assert "client-secret" not in example


def test_env_file_secret_path_overrides_yaml_secret_file_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    yaml_secret = tmp_path / "yaml-db.secret"
    yaml_secret.write_text("postgresql://yaml-file/db\n", encoding="utf-8")
    env_secret = tmp_path / "env-db.secret"
    env_secret.write_text("postgresql://env-file/db\n", encoding="utf-8")
    config_path = _write_config(
        tmp_path / "team-cloud.yaml",
        ["database_url_file: " + str(yaml_secret)],
    )
    monkeypatch.setenv("TEAM_CLOUD_DATABASE_URL_FILE", str(env_secret))

    from team_cloud.config import load_config

    config = load_config(config_path)

    assert config.database_url.get_secret_value() == "postgresql://env-file/db"


def test_yaml_direct_value_overrides_secret_file_sources(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    yaml_secret = tmp_path / "yaml-db.secret"
    yaml_secret.write_text("postgresql://yaml-file/db\n", encoding="utf-8")
    env_secret = tmp_path / "env-db.secret"
    env_secret.write_text("postgresql://env-file/db\n", encoding="utf-8")
    config_path = _write_config(
        tmp_path / "team-cloud.yaml",
        [
            "database_url: postgresql://yaml-direct/db",
            "database_url_file: " + str(yaml_secret),
        ],
    )
    monkeypatch.setenv("TEAM_CLOUD_DATABASE_URL_FILE", str(env_secret))

    from team_cloud.config import load_config

    config = load_config(config_path)

    assert config.database_url.get_secret_value() == "postgresql://yaml-direct/db"


def test_secret_file_preflight_reports_missing_files_without_values(tmp_path: Path):
    missing = tmp_path / "missing-db.secret"
    config_path = _write_config(
        tmp_path / "team-cloud.yaml",
        ["database_url_file: " + str(missing)],
    )

    from team_cloud.config import SecretFileError, load_config, validate_secret_files

    statuses = validate_secret_files(config_path)
    assert len(statuses) == 1
    assert statuses[0].field_name == "database_url"
    assert statuses[0].exists is False
    assert statuses[0].readable is False

    with pytest.raises(SecretFileError) as exc_info:
        load_config(config_path)

    error = str(exc_info.value)
    assert "database_url" in error
    assert str(missing) in error
    assert "postgresql://" not in error


def test_config_artifact_examples_match_env_schema():
    from team_cloud.config import ENV_SCHEMA

    artifact_dir = Path("teamDoc/GADoc/artifacts/team-cloud")
    env_example = (artifact_dir / "team-cloud.env.example").read_text(encoding="utf-8")
    config_example = (artifact_dir / "team-cloud.config.example.yaml").read_text(
        encoding="utf-8"
    )

    for env_name in REQUIRED_FILE_SECRET_ENVS:
        assert env_name in env_example
        assert ENV_SCHEMA[env_name].field_name in config_example

    assert "postgresql://" not in env_example
    assert "client-secret" not in env_example
