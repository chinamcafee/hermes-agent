from __future__ import annotations

import json
import os
from pathlib import Path


ARTIFACT = Path("teamDoc/GADoc/artifacts/release/team-cloud-training-material-v0.json")
DOC = Path("teamDoc/GADoc/P5-11-training-material.md")
SCRIPT = Path("scripts/team-cloud-training-material.py")
SMOKE_SCRIPT = Path("scripts/team-cloud-foundation-smoke.sh")
SMOKE_MATRIX = Path("teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json")


def test_training_material_covers_admin_member_faq_and_labs():
    from team_cloud.training_material import build_training_material_package

    package = build_training_material_package()
    modules = {module["id"]: module for module in package["modules"]}

    assert package["schema_version"] == 1
    assert package["name"] == "team-cloud-training-material-v0"
    assert {"admin_training", "member_training", "faq"} <= set(modules)
    assert {
        "organization_setup",
        "member_lifecycle",
        "tool_policy_management",
        "backup_restore_operations",
    } <= set(modules["admin_training"]["topics"])
    assert {
        "first_login",
        "team_chat",
        "personal_memory",
        "team_shared_memory",
    } <= set(modules["member_training"]["topics"])
    assert {
        "identity_map",
        "permission_denied",
        "backup_restore",
        "offline_bundle",
    } <= set(modules["faq"]["topics"])
    assert {
        "create_org_and_invite_member",
        "memory_review_flow",
        "run_foundation_smoke",
    } <= set(package["hands_on_labs"])


def test_training_material_artifact_script_docs_and_smoke_are_registered():
    from team_cloud.training_material import build_training_material_package

    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    doc = DOC.read_text(encoding="utf-8")
    script = SCRIPT.read_text(encoding="utf-8")
    smoke = SMOKE_SCRIPT.read_text(encoding="utf-8")
    matrix = json.loads(SMOKE_MATRIX.read_text(encoding="utf-8"))
    domains = {entry["domain"] for entry in matrix["checks"]}

    assert artifact == build_training_material_package()
    assert os.access(SCRIPT, os.X_OK)
    assert "team-cloud-training-material-v0.json" in script
    assert "管理员培训" in doc
    assert "成员培训" in doc
    assert "FAQ" in doc
    assert "create_org_and_invite_member" in doc
    assert "tests/team_cloud/test_training_material.py" in smoke
    assert "training_material" in domains
