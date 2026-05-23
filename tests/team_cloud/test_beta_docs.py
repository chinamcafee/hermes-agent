from __future__ import annotations

import json
import os
from pathlib import Path


ARTIFACT = Path("teamDoc/GADoc/artifacts/pilot/team-cloud-beta-docs-v0.json")
DOC = Path("teamDoc/GADoc/P4-14-beta-docs.md")
SCRIPT = Path("scripts/team-cloud-beta-docs.py")
SMOKE_SCRIPT = Path("scripts/team-cloud-foundation-smoke.sh")
SMOKE_MATRIX = Path("teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json")


def test_beta_documentation_package_covers_pilot_guides_known_issues_and_exit_criteria():
    from team_cloud.beta_docs import build_beta_documentation_package

    package = build_beta_documentation_package()
    documents = {item["id"]: item for item in package["documents"]}
    evidence = package["evidence_index"]

    assert package["schema_version"] == 1
    assert package["name"] == "team-cloud-beta-docs-v0"
    assert {
        "pilot_install_quickstart",
        "pilot_onboarding_guide",
        "feedback_and_triage_guide",
        "known_issues",
        "beta_exit_checklist",
    } <= set(documents)
    assert documents["pilot_install_quickstart"]["required_artifacts"] == [
        "P4-01-compose-hardening",
        "P4-02-helm-chart",
        "P4-03-offline-bundle",
        "P4-09-upgrade-rollback",
    ]
    assert documents["pilot_onboarding_guide"]["source_artifact"].endswith(
        "team-cloud-pilot-onboarding-v0.json"
    )
    assert documents["feedback_and_triage_guide"]["source_artifact"].endswith(
        "team-cloud-bug-triage-v0.json"
    )
    assert "helm_lint_requires_helm_binary" in documents["known_issues"]["items"]
    assert "live_services_required_for_restore_drills" in documents["known_issues"]["items"]
    assert package["feedback"]["required_fields"] == [
        "severity",
        "workflow",
        "impact",
        "repro_steps",
    ]
    assert "cross_org_access" in package["release_blocker_rules"]
    assert "security" in evidence
    assert "load" in evidence
    assert "chaos" in evidence
    assert "backup_restore" in evidence


def test_beta_docs_artifact_script_docs_and_smoke_are_registered():
    from team_cloud.beta_docs import build_beta_documentation_package

    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    doc = DOC.read_text(encoding="utf-8")
    script = SCRIPT.read_text(encoding="utf-8")
    smoke = SMOKE_SCRIPT.read_text(encoding="utf-8")
    matrix = json.loads(SMOKE_MATRIX.read_text(encoding="utf-8"))
    domains = {entry["domain"] for entry in matrix["checks"]}

    assert artifact == build_beta_documentation_package()
    assert os.access(SCRIPT, os.X_OK)
    assert "team-cloud-beta-docs-v0.json" in script
    assert "pilot_install_quickstart" in doc
    assert "known_issues" in doc
    assert "feedback_and_triage_guide" in doc
    assert "tests/team_cloud/test_beta_docs.py" in smoke
    assert "beta_docs" in domains
