from __future__ import annotations

import json
import os
from pathlib import Path


ARTIFACT = Path("teamDoc/GADoc/artifacts/release/team-cloud-legal-compliance-v0.json")
DOC = Path("teamDoc/GADoc/P5-14-legal-compliance-package.md")
SCRIPT = Path("scripts/team-cloud-legal-compliance.py")
SMOKE_SCRIPT = Path("scripts/team-cloud-foundation-smoke.sh")
SMOKE_MATRIX = Path("teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json")


def test_legal_compliance_package_collects_release_legal_and_security_evidence():
    from team_cloud.legal_compliance import build_legal_compliance_package

    package = build_legal_compliance_package()
    evidence = {item["id"]: item for item in package["evidence"]}

    assert package["schema_version"] == 1
    assert package["name"] == "team-cloud-legal-compliance-v0"
    assert {
        "sbom_license",
        "minio_agpl_notice",
        "final_security_review",
        "data_governance",
        "privacy_export_delete_retention",
    } <= set(evidence)
    assert evidence["sbom_license"]["artifact"] == (
        "teamDoc/GADoc/artifacts/release/team-cloud-sbom-license-v0.json"
    )
    assert evidence["final_security_review"]["artifact"] == (
        "teamDoc/GADoc/artifacts/security/team-cloud-final-security-review-v0.json"
    )
    assert "P3-20-data-governance-runbooks.md" in evidence["data_governance"]["documents"]
    assert {
        "org_export",
        "deletion_request",
        "retention_policies",
    } <= set(evidence["privacy_export_delete_retention"]["controls"])
    assert "customer_notice_required" in evidence["minio_agpl_notice"]["obligations"]
    assert package["acceptance_thresholds"]["unknown_licenses"] == 0
    assert package["acceptance_thresholds"]["open_critical_or_high_security_findings"] == 0
    assert package["exit_decision"] == "required_for_ga"


def test_legal_compliance_artifact_script_docs_and_smoke_are_registered():
    from team_cloud.legal_compliance import build_legal_compliance_package

    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    doc = DOC.read_text(encoding="utf-8")
    script = SCRIPT.read_text(encoding="utf-8")
    smoke = SMOKE_SCRIPT.read_text(encoding="utf-8")
    matrix = json.loads(SMOKE_MATRIX.read_text(encoding="utf-8"))
    domains = {entry["domain"] for entry in matrix["checks"]}

    assert artifact == build_legal_compliance_package()
    assert os.access(SCRIPT, os.X_OK)
    assert "team-cloud-legal-compliance-v0.json" in script
    assert "SBOM" in doc
    assert "许可证" in doc
    assert "数据治理" in doc
    assert "安全证据" in doc
    assert "tests/team_cloud/test_legal_compliance_package.py" in smoke
    assert "legal_compliance_package" in domains
