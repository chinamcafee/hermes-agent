from __future__ import annotations

import json
import os
from pathlib import Path


ARTIFACT = Path("teamDoc/GADoc/artifacts/release/team-cloud-ga-release-notes-v0.json")
DOC = Path("teamDoc/GADoc/P5-07-release-notes.md")
SCRIPT = Path("scripts/team-cloud-release-notes.py")
SMOKE_SCRIPT = Path("scripts/team-cloud-foundation-smoke.sh")
SMOKE_MATRIX = Path("teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json")


def test_release_notes_cover_ga_highlights_upgrade_notes_and_nonblocking_issues():
    from team_cloud.release_notes import build_release_notes_package

    notes = build_release_notes_package()
    breaking_changes = {item["id"] for item in notes["breaking_changes"]}
    upgrade_notes = {item["id"] for item in notes["upgrade_notes"]}
    evidence = {item["id"] for item in notes["evidence_links"]}

    assert notes["schema_version"] == 1
    assert notes["name"] == "team-cloud-ga-release-notes-v0"
    assert notes["release_channel"] == "GA"
    assert notes["release_status"] == "ga_ready"
    assert "enterprise_team_cloud" in notes["highlights"]
    assert "two_tier_memory" in notes["highlights"]
    assert "local_memory_backup" in notes["highlights"]
    assert {"casdoor_identity_required", "team_scoped_memory", "tool_policy_enforced"} <= (
        breaking_changes
    )
    assert {"compose", "helm", "offline_bundle", "migration_checksums"} <= upgrade_notes
    assert all(issue["ga_blocking"] is False for issue in notes["known_issues"])
    assert {"final_security_review", "sbom_license", "install_guide", "runbook_summary"} <= (
        evidence
    )


def test_release_notes_artifact_script_docs_and_smoke_are_registered():
    from team_cloud.release_notes import build_release_notes_package

    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    doc = DOC.read_text(encoding="utf-8")
    script = SCRIPT.read_text(encoding="utf-8")
    smoke = SMOKE_SCRIPT.read_text(encoding="utf-8")
    matrix = json.loads(SMOKE_MATRIX.read_text(encoding="utf-8"))
    domains = {entry["domain"] for entry in matrix["checks"]}

    assert artifact == build_release_notes_package()
    assert os.access(SCRIPT, os.X_OK)
    assert "team-cloud-ga-release-notes-v0.json" in script
    assert "breaking_changes" in doc
    assert "upgrade_notes" in doc
    assert "known_issues" in doc
    assert "offline_bundle" in doc
    assert "tests/team_cloud/test_release_notes.py" in smoke
    assert "release_notes" in domains
