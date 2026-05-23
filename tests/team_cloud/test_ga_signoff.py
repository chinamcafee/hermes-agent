from __future__ import annotations

import json
import os
from pathlib import Path


ARTIFACT = Path("teamDoc/GADoc/artifacts/release/team-cloud-ga-sign-off-v0.json")
DOC = Path("teamDoc/GADoc/P5-08-ga-sign-off.md")
SCRIPT = Path("scripts/team-cloud-ga-sign-off.py")
SMOKE_SCRIPT = Path("scripts/team-cloud-foundation-smoke.sh")
SMOKE_MATRIX = Path("teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json")


def test_ga_signoff_register_covers_required_domains_and_evidence():
    from team_cloud.ga_signoff import build_ga_signoff_package

    package = build_ga_signoff_package()
    signoffs = {item["domain"]: item for item in package["signoffs"]}
    evidence = {item["id"] for item in package["evidence_links"]}

    assert package["schema_version"] == 1
    assert package["name"] == "team-cloud-ga-sign-off-v0"
    assert package["gate"] == "ga"
    assert package["m5_final_signoff"] == "signed"
    assert {
        "product_requirements",
        "authn_authz",
        "memory_isolation",
        "backup_restore",
        "web_console",
        "documentation",
        "security_review",
        "pilot_acceptance",
        "release_operations",
    } <= set(signoffs)
    assert signoffs["security_review"]["owner"] == "Security"
    assert signoffs["documentation"]["owner"] == "Product + Engineering"
    assert package["blocking_issues"] == {"p0_open": 0, "p1_open": 0}
    assert {
        "final_security_review",
        "beta_exit_report",
        "release_notes",
        "runbook_summary",
        "final_regression",
        "deployment_smoke",
        "legal_compliance",
        "post_ga_backlog",
    } <= evidence


def test_ga_signoff_artifact_script_docs_and_smoke_are_registered():
    from team_cloud.ga_signoff import build_ga_signoff_package

    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    doc = DOC.read_text(encoding="utf-8")
    script = SCRIPT.read_text(encoding="utf-8")
    smoke = SMOKE_SCRIPT.read_text(encoding="utf-8")
    matrix = json.loads(SMOKE_MATRIX.read_text(encoding="utf-8"))
    domains = {entry["domain"] for entry in matrix["checks"]}

    assert artifact == build_ga_signoff_package()
    assert os.access(SCRIPT, os.X_OK)
    assert "team-cloud-ga-sign-off-v0.json" in script
    assert "Product requirements" in doc
    assert "AuthN/AuthZ" in doc
    assert "Memory isolation" in doc
    assert "M5 final sign-off signed" in doc
    assert "tests/team_cloud/test_ga_signoff.py" in smoke
    assert "ga_signoff" in domains
