from __future__ import annotations

import json
import os
from pathlib import Path


ARTIFACT = Path("teamDoc/GADoc/artifacts/release/team-cloud-final-regression-v0.json")
DOC = Path("teamDoc/GADoc/P5-12-final-regression.md")
SCRIPT = Path("scripts/team-cloud-final-regression.py")
SMOKE_SCRIPT = Path("scripts/team-cloud-foundation-smoke.sh")
SMOKE_MATRIX = Path("teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json")


def test_final_regression_covers_full_negative_backup_and_permission_gates():
    from team_cloud.final_regression import build_final_regression_package

    package = build_final_regression_package()
    gates = {gate["id"]: gate for gate in package["gates"]}

    assert package["schema_version"] == 1
    assert package["name"] == "team-cloud-final-regression-v0"
    assert {
        "full_foundation_smoke",
        "security_negative_suite",
        "backup_restore_drill",
        "permission_matrix",
    } <= set(gates)
    assert gates["full_foundation_smoke"]["command"] == "scripts/team-cloud-foundation-smoke.sh"
    assert "tests/team_cloud/test_platform_security_negative.py" in gates["security_negative_suite"]["command"]
    assert "tests/team_cloud/test_platform_backup_restore_drill.py" in gates["backup_restore_drill"]["command"]
    assert {
        "tests/team_cloud/test_permission_explorer_ga.py",
        "tests/team_cloud/test_team_tool_policy_hook.py",
        "tests/team_cloud/test_authz_chaos.py",
    } <= set(gates["permission_matrix"]["test_files"])
    assert package["acceptance_thresholds"]["failed_tests"] == 0
    assert package["acceptance_thresholds"]["open_critical_or_high_findings"] == 0
    assert package["exit_decision"] == "required_for_ga"


def test_final_regression_artifact_script_docs_and_smoke_are_registered():
    from team_cloud.final_regression import build_final_regression_package

    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    doc = DOC.read_text(encoding="utf-8")
    script = SCRIPT.read_text(encoding="utf-8")
    smoke = SMOKE_SCRIPT.read_text(encoding="utf-8")
    matrix = json.loads(SMOKE_MATRIX.read_text(encoding="utf-8"))
    domains = {entry["domain"] for entry in matrix["checks"]}

    assert artifact == build_final_regression_package()
    assert os.access(SCRIPT, os.X_OK)
    assert "team-cloud-final-regression-v0.json" in script
    assert "全量测试" in doc
    assert "负测" in doc
    assert "备份恢复" in doc
    assert "权限矩阵" in doc
    assert "scripts/team-cloud-foundation-smoke.sh" in doc
    assert "tests/team_cloud/test_final_regression.py" in smoke
    assert "final_regression" in domains
