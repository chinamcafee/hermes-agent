"""Upgrade and rollback plan contract for Team Cloud."""

from __future__ import annotations

from typing import Any

from team_cloud.migrations import MigrationRunner


def build_upgrade_rollback_plan() -> dict[str, Any]:
    migrations = MigrationRunner.default().dry_run()
    checksums = dict(migrations["checksums"])
    return {
        "schema_version": 1,
        "name": "team-cloud-upgrade-rollback-v0",
        "preconditions": [
            "P4-06 backup_restore_drill succeeded",
            "P4-08 security_test_suite succeeded",
            "maintenance window approved",
        ],
        "steps": [
            {
                "id": "preflight_backup",
                "forward_command": "scripts/team-cloud-backup-restore-drill.py --output teamDoc/GADoc/artifacts/drills/team-cloud-backup-restore-drill-v0.json",
                "rollback_command": "block upgrade if backup drill status is not succeeded",
                "verification": "team-cloud-backup-restore-drill-v0.json status == succeeded",
            },
            {
                "id": "database_migrations",
                "forward_command": _migration_forward_command(migrations["migrations"]),
                "rollback_command": "restore PostgreSQL PITR snapshot from P4-06 preflight backup",
                "verification": "MigrationRunner.default().dry_run() checksums match artifact",
                "migration_checksums": checksums,
            },
            {
                "id": "spicedb_schema_compatibility",
                "forward_command": "zed validate teamDoc/GADoc/artifacts/spicedb/schema-v0.zed && zed test teamDoc/GADoc/artifacts/spicedb/schema-v0-validation.yaml",
                "rollback_command": "re-apply previous schema.zed and replay relationship snapshot",
                "verification": "permission fixture positive and negative cases pass",
            },
            {
                "id": "helm_or_compose_deploy",
                "forward_command": "helm upgrade --install hermes-team-cloud deploy/team-cloud/helm/hermes-team-cloud --atomic --wait",
                "rollback_command": "docker compose -f deploy/team-cloud/compose.yaml up -d --remove-orphans previous image tags",
                "verification": "team-api /healthz and /readyz return ok",
            },
            {
                "id": "offline_bundle_upgrade",
                "forward_command": "deploy/team-cloud/offline/install.sh --manifest deploy/team-cloud/offline/manifest.yaml",
                "rollback_command": "deploy/team-cloud/offline/install.sh --manifest previous-offline-manifest.yaml",
                "verification": "offline manifest checksum verification passes",
            },
            {
                "id": "post_upgrade_smoke",
                "forward_command": "scripts/team-cloud-foundation-smoke.sh",
                "rollback_command": "run image_rollback then database_restore_rollback",
                "verification": "scripts/team-cloud-foundation-smoke.sh passes",
            },
            {
                "id": "image_rollback",
                "forward_command": "record current image digests before upgrade",
                "rollback_command": "helm rollback hermes-team-cloud 1 --wait",
                "verification": "deployment image digests match previous release",
            },
            {
                "id": "database_restore_rollback",
                "forward_command": "record PITR target and migration checksums before upgrade",
                "rollback_command": "restore PostgreSQL PITR snapshot and replay pre-upgrade SpiceDB snapshot",
                "verification": "migration checksums and SpiceDB schema hash match previous release",
            },
        ],
    }


def _migration_forward_command(migration_names: object) -> str:
    names = [str(name) for name in migration_names]
    return " && ".join(
        f"psql --set ON_ERROR_STOP=1 $TEAM_CLOUD_DATABASE_URL -f team_cloud/sql_migrations/{name}"
        for name in names
    )


__all__ = ["build_upgrade_rollback_plan"]
