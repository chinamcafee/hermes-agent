"""Install guide package contract for Team Cloud GA."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


_INSTALL_PATHS: tuple[dict[str, Any], ...] = (
    {
        "id": "compose",
        "entrypoint": "deploy/team-cloud/compose.yaml",
        "target": "single-node or developer validation",
        "required_artifacts": [
            "deploy/team-cloud/secrets/*.txt",
            "teamDoc/GADoc/P1-22-foundation-deployment-docs.md",
        ],
        "commands": [
            "docker compose -f deploy/team-cloud/compose.yaml up --build",
            "scripts/team-cloud-foundation-smoke.sh",
        ],
    },
    {
        "id": "helm",
        "entrypoint": "deploy/team-cloud/helm/hermes-team-cloud/Chart.yaml",
        "target": "Kubernetes production or staging",
        "required_artifacts": [
            "deploy/team-cloud/helm/hermes-team-cloud/values.yaml",
            "teamDoc/GADoc/P4-02-helm-chart.md",
        ],
        "commands": [
            "helm upgrade --install hermes-team-cloud deploy/team-cloud/helm/hermes-team-cloud --atomic --wait",
            "scripts/team-cloud-foundation-smoke.sh",
        ],
    },
    {
        "id": "offline_bundle",
        "entrypoint": "deploy/team-cloud/offline/install.sh",
        "target": "air-gapped or restricted-network install",
        "required_artifacts": [
            "deploy/team-cloud/offline/manifest.yaml",
            "deploy/team-cloud/offline/images/",
            "checksums",
        ],
        "commands": [
            "scripts/team-cloud-offline-bundle.sh --manifest deploy/team-cloud/offline/manifest.yaml",
            "deploy/team-cloud/offline/install.sh --manifest deploy/team-cloud/offline/manifest.yaml",
        ],
    },
)


def build_install_guide_package() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "name": "team-cloud-install-guide-v0",
        "install_paths": deepcopy(list(_INSTALL_PATHS)),
        "preflight_checks": [
            "python_3_11",
            "container_runtime",
            "ports_available",
            "secrets_present",
            "casdoor_redirect_urls",
            "spicedb_preshared_key",
            "minio_bucket_policy",
        ],
        "first_login": {
            "identity_provider": "Casdoor",
            "steps": [
                "owner_bootstrap",
                "create_organization",
                "invite_admin",
                "verify_spicedb_relationships",
                "run_foundation_smoke",
            ],
        },
        "health_checks": [
            "team_api",
            "casdoor",
            "spicedb",
            "postgres",
            "minio",
            "worker",
            "web_shell",
        ],
        "troubleshooting": {
            "spicedb_schema_load_failure": [
                "Confirm spicedb-migrate and spicedb-schema-load completed.",
                "Verify TEAM_CLOUD_SPICEDB_PRESHARED_KEY_FILE is mounted.",
                "Run scripts/run_tests.sh tests/team_cloud/test_spicedb_schema_ci.py.",
            ],
            "casdoor_oidc_redirect_failure": [
                "Confirm browser URL matches Casdoor redirect allowlist.",
                "Verify TEAM_CLOUD_JWT_ISSUER and client_id are aligned.",
            ],
            "postgres_migration_failure": [
                "Confirm TEAM_CLOUD_DATABASE_URL_FILE exists and points at the Team Cloud database.",
                "Run scripts/run_tests.sh tests/team_cloud/test_postgres_migrations.py.",
            ],
            "minio_manifest_failure": [
                "Confirm MinIO endpoint, access key, secret key, and bucket bootstrap.",
                "Run scripts/run_tests.sh tests/team_cloud/test_minio_manifest.py.",
            ],
        },
        "verification": [
            "scripts/run_tests.sh tests/team_cloud/test_install_guide.py",
            "scripts/team-cloud-foundation-smoke.sh",
        ],
    }


__all__ = ["build_install_guide_package"]
