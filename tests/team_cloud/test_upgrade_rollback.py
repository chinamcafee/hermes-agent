from __future__ import annotations

import json
import os
from pathlib import Path


ARTIFACT = Path("teamDoc/GADoc/artifacts/release/team-cloud-upgrade-rollback-v0.json")
DOC = Path("teamDoc/GADoc/P4-09-upgrade-rollback.md")
SCRIPT = Path("scripts/team-cloud-upgrade-rollback-plan.py")
SMOKE_SCRIPT = Path("scripts/team-cloud-foundation-smoke.sh")
SMOKE_MATRIX = Path("teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json")

REQUIRED_STEPS = {
    "preflight_backup",
    "database_migrations",
    "spicedb_schema_compatibility",
    "helm_or_compose_deploy",
    "offline_bundle_upgrade",
    "post_upgrade_smoke",
    "image_rollback",
    "database_restore_rollback",
}


def test_upgrade_rollback_plan_covers_migrations_images_and_schema_compatibility():
    from team_cloud.upgrade import build_upgrade_rollback_plan

    plan = build_upgrade_rollback_plan()
    steps = {step["id"]: step for step in plan["steps"]}

    assert plan["schema_version"] == 1
    assert plan["name"] == "team-cloud-upgrade-rollback-v0"
    assert set(steps) == REQUIRED_STEPS
    assert steps["database_migrations"]["forward_command"].startswith("psql ")
    assert "001_schema_v0.sql" in steps["database_migrations"]["migration_checksums"]
    assert "002_memory_runtime_schema.sql" in steps["database_migrations"][
        "migration_checksums"
    ]
    assert "schema-v0.zed" in steps["spicedb_schema_compatibility"]["forward_command"]
    assert "helm rollback" in steps["image_rollback"]["rollback_command"]
    assert "scripts/team-cloud-foundation-smoke.sh" in steps["post_upgrade_smoke"][
        "verification"
    ]
    assert all(step["rollback_command"] for step in plan["steps"])


def test_upgrade_rollback_artifact_script_docs_and_smoke_are_registered():
    from team_cloud.upgrade import build_upgrade_rollback_plan

    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    doc = DOC.read_text(encoding="utf-8")
    script = SCRIPT.read_text(encoding="utf-8")
    smoke = SMOKE_SCRIPT.read_text(encoding="utf-8")
    matrix = json.loads(SMOKE_MATRIX.read_text(encoding="utf-8"))
    domains = {entry["domain"] for entry in matrix["checks"]}

    assert artifact == build_upgrade_rollback_plan()
    assert os.access(SCRIPT, os.X_OK)
    assert "team-cloud-upgrade-rollback-v0.json" in script
    assert "database_migrations" in doc
    assert "spicedb_schema_compatibility" in doc
    assert "image_rollback" in doc
    assert "tests/team_cloud/test_upgrade_rollback.py" in smoke
    assert "upgrade_rollback" in domains
