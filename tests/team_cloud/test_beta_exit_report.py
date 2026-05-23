from __future__ import annotations

import json
import os
from pathlib import Path


ARTIFACT = Path("teamDoc/GADoc/artifacts/pilot/team-cloud-beta-exit-report-v0.json")
DOC = Path("teamDoc/GADoc/P4-18-beta-exit-report.md")
SCRIPT = Path("scripts/team-cloud-beta-exit-report.py")
SMOKE_SCRIPT = Path("scripts/team-cloud-foundation-smoke.sh")
SMOKE_MATRIX = Path("teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json")


def test_beta_exit_report_rolls_up_blockers_readiness_and_residual_risks():
    from team_cloud.beta_exit import build_beta_exit_report

    report = build_beta_exit_report()
    readiness_domains = {item["domain"] for item in report["ga_readiness"]}

    assert report["schema_version"] == 1
    assert report["name"] == "team-cloud-beta-exit-report-v0"
    assert report["exit_recommendation"] == "proceed_to_p5"
    assert report["blockers"]["open_p0_p1"] == 0
    assert report["blockers"]["security_data_leak"] == 0
    assert report["blockers"]["cross_org_access"] == 0
    assert report["blockers"]["backup_restore_failure"] == 0
    assert {
        "deployment",
        "observability",
        "load",
        "security",
        "backup_restore",
        "pilot",
        "docs",
        "accessibility",
        "performance",
    } <= readiness_domains
    assert "final_security_review" in report["p5_followups"]
    assert "sbom_license_package" in report["p5_followups"]
    assert {
        "deployment_smoke_helm_runtime_validation",
        "final_regression",
        "legal_compliance_package",
        "admin_user_manuals",
        "api_docs",
        "runbook_summary",
        "release_manual",
    } <= set(report["p5_followups"])
    assert all(item["owner"] for item in report["residual_risks"])

    matrix_items = {item["id"]: item for item in report["ga_matrix_coverage"]}
    required = {
        "GA-SEC-001",
        "GA-SEC-004",
        "GA-SEC-005",
        "GA-SEC-007",
        "GA-PERF-001",
        "GA-BR-001",
        "GA-BR-005",
        "GA-REL-001",
        "GA-REL-002",
        "GA-REL-003",
        "GA-PILOT-001",
        "GA-PILOT-002",
    }
    assert required <= set(matrix_items)
    assert all(item["status"] in {"passed", "p5_followup"} for item in matrix_items.values())
    assert all(item["ga_blocking"] is True or item["status"] == "p5_followup" for item in matrix_items.values())

    blocking_followups = {
        item["id"] for item in matrix_items.values() if item["ga_blocking"] is True and item["status"] == "p5_followup"
    }
    assert {"GA-REL-002", "GA-REL-004", "GA-REL-005", "GA-DOC-001", "GA-DOC-002", "GA-DOC-003", "GA-DOC-004", "GA-SIGN-001"} <= blocking_followups


def test_beta_exit_report_artifact_script_docs_and_smoke_are_registered():
    from team_cloud.beta_exit import build_beta_exit_report

    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    doc = DOC.read_text(encoding="utf-8")
    script = SCRIPT.read_text(encoding="utf-8")
    smoke = SMOKE_SCRIPT.read_text(encoding="utf-8")
    matrix = json.loads(SMOKE_MATRIX.read_text(encoding="utf-8"))
    domains = {entry["domain"] for entry in matrix["checks"]}

    assert artifact == build_beta_exit_report()
    assert os.access(SCRIPT, os.X_OK)
    assert "team-cloud-beta-exit-report-v0.json" in script
    assert "exit_recommendation" in doc
    assert "ga_readiness" in doc
    assert "GA-SEC-001" in doc
    assert "GA-REL-002" in doc
    assert "GA-PILOT-001" in doc
    assert "residual_risks" in doc
    assert "tests/team_cloud/test_beta_exit_report.py" in smoke
    assert "beta_exit_report" in domains
