from __future__ import annotations

from pathlib import Path


DEPLOY_DOC = Path("teamDoc/GADoc/P1-22-foundation-deployment-docs.md")


def test_foundation_deployment_doc_covers_local_setup_config_and_troubleshooting():
    content = DEPLOY_DOC.read_text(encoding="utf-8")

    assert "docker compose -f deploy/team-cloud/compose.yaml up" in content
    assert "scripts/team-cloud-foundation-smoke.sh" in content
    assert "TEAM_CLOUD_DATABASE_URL_FILE" in content
    assert "TEAM_CLOUD_CASDOOR_CLIENT_SECRET_FILE" in content
    assert "TEAM_CLOUD_SPICEDB_PRESHARED_KEY_FILE" in content
    assert "TEAM_CLOUD_MINIO_SECRET_KEY_FILE" in content
    assert "Casdoor" in content
    assert "SpiceDB" in content
    assert "PostgreSQL" in content
    assert "MinIO" in content
    assert "Troubleshooting" in content


def test_foundation_deployment_doc_lists_local_ports_and_health_checks():
    content = DEPLOY_DOC.read_text(encoding="utf-8")

    for port in ("8780", "8781", "18000", "50051", "19000", "19001"):
        assert port in content

    assert "/healthz" in content
    assert "/readyz" in content
    assert "/metrics" in content
