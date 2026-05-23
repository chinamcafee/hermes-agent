from __future__ import annotations

from pathlib import Path


CHECKLIST = Path("teamDoc/16-ga-test-release-checklist.md")
SMOKE_SCRIPT = Path("scripts/team-cloud-foundation-smoke.sh")
SMOKE_MATRIX = Path("teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json")


def test_ga_release_checklist_signoff_matches_m5_signed_state():
    content = CHECKLIST.read_text(encoding="utf-8")

    assert "| Product requirements | Product | signed |" in content
    assert "| AuthN/AuthZ | Backend + Security | signed |" in content
    assert "| Memory isolation | Runtime + QA | signed |" in content
    assert "| Backup/restore | SRE | signed |" in content
    assert "| Web Console | Frontend | signed |" in content
    assert "| Documentation | Product + Engineering | signed |" in content
    assert "| Security review | Security | signed |" in content
    assert "| Pilot acceptance | Customer/Internal | signed |" in content
    assert "| Release operations | Release | signed |" in content
    assert "M5 GA Sign-off" in content
    assert "team-cloud-ga-sign-off-v0.json" in content


def test_ga_release_checklist_is_in_foundation_smoke():
    smoke = SMOKE_SCRIPT.read_text(encoding="utf-8")
    matrix = SMOKE_MATRIX.read_text(encoding="utf-8")

    assert "tests/team_cloud/test_ga_release_checklist.py" in smoke
    assert "ga_release_checklist" in matrix
