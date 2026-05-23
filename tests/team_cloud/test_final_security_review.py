from __future__ import annotations

import json
import os
from pathlib import Path


ARTIFACT = Path("teamDoc/GADoc/artifacts/security/team-cloud-final-security-review-v0.json")
DOC = Path("teamDoc/GADoc/P5-01-final-security-review.md")
SCRIPT = Path("scripts/team-cloud-final-security-review.py")
SMOKE_SCRIPT = Path("scripts/team-cloud-foundation-smoke.sh")
SMOKE_MATRIX = Path("teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json")


def test_final_security_review_closes_p0_p1_and_critical_high_risks():
    from team_cloud.final_security import build_final_security_review

    review = build_final_security_review()
    domains = {item["domain"]: item for item in review["review_domains"]}
    risk_statuses = {item["status"] for item in review["risk_disposition"]}

    assert review["schema_version"] == 1
    assert review["name"] == "team-cloud-final-security-review-v0"
    assert review["exit_criteria"]["p0_p1_security_defects"] == 0
    assert review["exit_criteria"]["critical_risks_open"] == 0
    assert review["exit_criteria"]["high_risks_open"] == 0
    assert review["exit_criteria"]["cross_tenant_access"] == 0
    assert review["exit_criteria"]["personal_memory_leakage"] == 0
    assert review["exit_criteria"]["high_risk_tool_bypass"] == 0
    assert {
        "authn_authz",
        "memory_isolation",
        "minio_backup_access",
        "tool_policy",
        "break_glass",
        "identity_headers",
        "audit_redaction",
    } <= set(domains)
    assert all(item["evidence"] for item in domains.values())
    assert risk_statuses == {"closed"}
    assert any("test_platform_security_negative.py" in command for command in review["required_commands"])
    assert any("test_isolation_suite.py" in command for command in review["required_commands"])


def test_final_security_review_artifact_script_docs_and_smoke_are_registered():
    from team_cloud.final_security import build_final_security_review

    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    doc = DOC.read_text(encoding="utf-8")
    script = SCRIPT.read_text(encoding="utf-8")
    smoke = SMOKE_SCRIPT.read_text(encoding="utf-8")
    matrix = json.loads(SMOKE_MATRIX.read_text(encoding="utf-8"))
    domains = {entry["domain"] for entry in matrix["checks"]}

    assert artifact == build_final_security_review()
    assert os.access(SCRIPT, os.X_OK)
    assert "team-cloud-final-security-review-v0.json" in script
    assert "p0_p1_security_defects" in doc
    assert "risk_disposition" in doc
    assert "memory_isolation" in doc
    assert "tests/team_cloud/test_final_security_review.py" in smoke
    assert "final_security_review" in domains
