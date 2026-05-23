from __future__ import annotations

import json
import os
from pathlib import Path


ARTIFACT = Path("teamDoc/GADoc/artifacts/security/team-cloud-security-suite-v0.json")
DOC = Path("teamDoc/GADoc/P4-08-security-test-suite.md")
SCRIPT = Path("scripts/team-cloud-security-suite.py")
SMOKE_SCRIPT = Path("scripts/team-cloud-foundation-smoke.sh")
SMOKE_MATRIX = Path("teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json")

REQUIRED_CASES = {
    "forged_casdoor_token",
    "wrong_audience_issuer",
    "disabled_member_access",
    "cross_org_memory_query",
    "prompt_injection_personal_memory_exfiltration",
    "tool_bypass_high_risk",
    "break_glass_abuse",
    "minio_signed_url_cross_org",
}


def test_security_suite_catalog_covers_p4_attack_cases():
    from team_cloud.security_suite import build_security_test_suite

    suite = build_security_test_suite()
    cases = {case["id"]: case for case in suite["cases"]}

    assert suite["schema_version"] == 1
    assert suite["name"] == "team-cloud-security-suite-v0"
    assert set(cases) == REQUIRED_CASES
    assert cases["forged_casdoor_token"]["severity"] == "critical"
    assert cases["wrong_audience_issuer"]["control"] == "jwt_middleware"
    assert "context_fencing" in cases[
        "prompt_injection_personal_memory_exfiltration"
    ]["required_controls"]
    assert "approval_required" in cases["tool_bypass_high_risk"]["required_controls"]
    assert "two_person_approval" in cases["break_glass_abuse"]["required_controls"]
    assert cases["minio_signed_url_cross_org"]["expected_result"] == "deny"
    assert all(case["run_command"].startswith("scripts/run_tests.sh ") for case in suite["cases"])


def test_security_suite_artifact_script_docs_and_smoke_are_registered():
    from team_cloud.security_suite import build_security_test_suite

    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    doc = DOC.read_text(encoding="utf-8")
    script = SCRIPT.read_text(encoding="utf-8")
    smoke = SMOKE_SCRIPT.read_text(encoding="utf-8")
    matrix = json.loads(SMOKE_MATRIX.read_text(encoding="utf-8"))
    domains = {entry["domain"] for entry in matrix["checks"]}

    assert artifact == build_security_test_suite()
    assert os.access(SCRIPT, os.X_OK)
    assert "team-cloud-security-suite-v0.json" in script
    assert "prompt_injection_personal_memory_exfiltration" in doc
    assert "minio_signed_url_cross_org" in doc
    assert "tests/team_cloud/test_security_test_suite.py" in smoke
    assert "security_test_suite" in domains
