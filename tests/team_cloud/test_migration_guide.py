from __future__ import annotations

import json
import os
from pathlib import Path


ARTIFACT = Path("teamDoc/GADoc/artifacts/release/team-cloud-migration-guide-v0.json")
DOC = Path("teamDoc/GADoc/P5-10-migration-guide.md")
SCRIPT = Path("scripts/team-cloud-migration-guide.py")
SMOKE_SCRIPT = Path("scripts/team-cloud-foundation-smoke.sh")
SMOKE_MATRIX = Path("teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json")


def test_migration_guide_covers_sessiondb_legacy_memory_validation_and_rollback():
    from team_cloud.migration_guide import build_migration_guide_package

    package = build_migration_guide_package()
    paths = {path["id"]: path for path in package["migration_paths"]}

    assert package["schema_version"] == 1
    assert package["name"] == "team-cloud-migration-guide-v0"
    assert {
        "sessiondb_import",
        "legacy_memory_provider_export",
        "memory_scope_mapping",
        "dry_run_validation",
        "rollback_snapshot",
    } <= set(paths)
    assert paths["sessiondb_import"]["command"] == "scripts/team-cloud-import-sessiondb.py"
    assert "export_jsonl" in paths["legacy_memory_provider_export"]["required_format"]
    assert paths["memory_scope_mapping"]["target_scopes"] == ["personal", "team_shared"]
    assert {
        "unmapped_identity_report",
        "duplicate_conflict_review",
        "pii_secret_scan",
        "isolation_smoke",
        "backup_before_cutover",
    } <= set(package["validation_checks"])
    assert "restore_postgres_snapshot" in package["rollback_steps"]


def test_migration_guide_artifact_script_docs_and_smoke_are_registered():
    from team_cloud.migration_guide import build_migration_guide_package

    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    doc = DOC.read_text(encoding="utf-8")
    script = SCRIPT.read_text(encoding="utf-8")
    smoke = SMOKE_SCRIPT.read_text(encoding="utf-8")
    matrix = json.loads(SMOKE_MATRIX.read_text(encoding="utf-8"))
    domains = {entry["domain"] for entry in matrix["checks"]}

    assert artifact == build_migration_guide_package()
    assert os.access(SCRIPT, os.X_OK)
    assert "team-cloud-migration-guide-v0.json" in script
    assert "SessionDB" in doc
    assert "legacy memory provider" in doc
    assert "identity_map" in doc
    assert "dry_run" in doc
    assert "tests/team_cloud/test_migration_guide.py" in smoke
    assert "migration_guide" in domains
