from __future__ import annotations

import json
import os
from pathlib import Path


ARTIFACT = Path("teamDoc/GADoc/artifacts/release/team-cloud-admin-user-manuals-v0.json")
DOC = Path("teamDoc/GADoc/P5-04-admin-user-manuals.md")
SCRIPT = Path("scripts/team-cloud-admin-user-manuals.py")
SMOKE_SCRIPT = Path("scripts/team-cloud-foundation-smoke.sh")
SMOKE_MATRIX = Path("teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json")


def test_admin_user_manuals_cover_admin_and_member_workflows():
    from team_cloud.admin_user_manuals import build_admin_user_manual_package

    package = build_admin_user_manual_package()
    manuals = {manual["id"]: manual for manual in package["manuals"]}
    admin_sections = {section["id"] for section in manuals["admin"]["sections"]}
    user_sections = {section["id"] for section in manuals["user"]["sections"]}
    workflow_ids = {workflow["id"] for workflow in package["workflows"]}

    assert package["schema_version"] == 1
    assert package["name"] == "team-cloud-admin-user-manuals-v0"
    assert {"admin", "user"} <= set(manuals)
    assert manuals["admin"]["audience"] == "Org Owner and Team Admin"
    assert manuals["user"]["audience"] == "Team Member"
    assert {
        "organization_setup",
        "member_lifecycle",
        "role_permission_matrix",
        "memory_governance",
        "backup_restore_operations",
        "tool_policy_management",
        "audit_review",
    } <= admin_sections
    assert {
        "first_login",
        "team_chat",
        "personal_memory",
        "team_shared_memory",
        "review_queue",
        "backup_self_service",
        "tool_approval_requests",
    } <= user_sections
    assert {
        "org_member_management",
        "memory_review",
        "backup_restore",
        "tool_policy_change",
    } <= workflow_ids


def test_admin_user_manuals_artifact_script_docs_and_smoke_are_registered():
    from team_cloud.admin_user_manuals import build_admin_user_manual_package

    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    doc = DOC.read_text(encoding="utf-8")
    script = SCRIPT.read_text(encoding="utf-8")
    smoke = SMOKE_SCRIPT.read_text(encoding="utf-8")
    matrix = json.loads(SMOKE_MATRIX.read_text(encoding="utf-8"))
    domains = {entry["domain"] for entry in matrix["checks"]}

    assert artifact == build_admin_user_manual_package()
    assert os.access(SCRIPT, os.X_OK)
    assert "team-cloud-admin-user-manuals-v0.json" in script
    assert "organization_setup" in doc
    assert "member_lifecycle" in doc
    assert "personal_memory" in doc
    assert "team_shared_memory" in doc
    assert "backup_restore_operations" in doc
    assert "tool_policy_management" in doc
    assert "tests/team_cloud/test_admin_user_manuals.py" in smoke
    assert "admin_user_manuals" in domains
