from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def team_cloud_config_file(tmp_path: Path) -> Path:
    db_secret = tmp_path / "database_url.secret"
    db_secret.write_text("postgresql://secret-file/db\n", encoding="utf-8")

    oidc_secret = tmp_path / "oidc.secret"
    oidc_secret.write_text("yaml-client-secret\n", encoding="utf-8")

    config_file = tmp_path / "team-cloud.yaml"
    config_file.write_text(
        "\n".join(
            [
                "environment: yaml-env",
                "api_port: 9999",
                "database_url_file: " + str(db_secret),
                "oidc_client_secret_file: " + str(oidc_secret),
                "",
            ]
        ),
        encoding="utf-8",
    )
    return config_file


@pytest.fixture
def team_cloud_config(team_cloud_config_file: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("TEAM_CLOUD_API_PORT", "8780")
    monkeypatch.setenv("TEAM_CLOUD_DATABASE_URL", "postgresql://env/db")

    from team_cloud.config import load_config

    return load_config(team_cloud_config_file)
