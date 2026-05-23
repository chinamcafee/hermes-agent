"""Migration guide package contract for Team Cloud GA."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


_MIGRATION_PATHS: tuple[dict[str, Any], ...] = (
    {
        "id": "sessiondb_import",
        "source": "Hermes SessionDB",
        "command": "scripts/team-cloud-import-sessiondb.py",
        "required_inputs": ["db_path", "org_id", "team_id", "project_id", "identity_map"],
    },
    {
        "id": "legacy_memory_provider_export",
        "source": "legacy memory provider",
        "required_format": "export_jsonl with content, scope, member_id, team_id, metadata",
        "target": "Team Cloud Memory API",
    },
    {
        "id": "memory_scope_mapping",
        "source": "legacy memory records",
        "target_scopes": ["personal", "team_shared"],
        "rules": [
            "member-owned facts map to personal",
            "organization-approved shared facts map to team_shared",
        ],
    },
    {
        "id": "dry_run_validation",
        "source": "migration report",
        "command": "scripts/team-cloud-import-sessiondb.py --dry-run",
        "outputs": ["imported_session_count", "unmapped_session_count", "unmapped_sessions"],
    },
    {
        "id": "rollback_snapshot",
        "source": "pre-cutover snapshot",
        "steps": ["keep_sessiondb_readonly_snapshot", "restore_postgres_snapshot"],
    },
)


def build_migration_guide_package() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "name": "team-cloud-migration-guide-v0",
        "migration_paths": deepcopy(list(_MIGRATION_PATHS)),
        "validation_checks": [
            "unmapped_identity_report",
            "duplicate_conflict_review",
            "pii_secret_scan",
            "isolation_smoke",
            "backup_before_cutover",
        ],
        "rollback_steps": [
            "freeze_source_writes",
            "keep_sessiondb_readonly_snapshot",
            "restore_postgres_snapshot",
            "restore_minio_backup_objects",
            "rerun_foundation_smoke",
        ],
        "verification": [
            "scripts/run_tests.sh tests/team_cloud/test_migration_guide.py",
            "scripts/team-cloud-foundation-smoke.sh",
        ],
    }


__all__ = ["build_migration_guide_package"]
