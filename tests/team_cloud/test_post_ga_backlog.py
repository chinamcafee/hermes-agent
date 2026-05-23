from __future__ import annotations

import json
import os
from pathlib import Path


ARTIFACT = Path("teamDoc/GADoc/artifacts/release/team-cloud-post-ga-backlog-v0.json")
DOC = Path("teamDoc/GADoc/P5-15-post-ga-backlog.md")
SCRIPT = Path("scripts/team-cloud-post-ga-backlog.py")
SMOKE_SCRIPT = Path("scripts/team-cloud-foundation-smoke.sh")
SMOKE_MATRIX = Path("teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json")


def test_post_ga_backlog_tracks_non_blocking_followups_and_final_signoff():
    from team_cloud.ga_signoff import build_ga_signoff_package
    from team_cloud.post_ga_backlog import build_post_ga_backlog_package

    package = build_post_ga_backlog_package()
    items = {item["id"]: item for item in package["items"]}
    signoff = build_ga_signoff_package()
    evidence = {item["id"] for item in signoff["evidence_links"]}

    assert package["schema_version"] == 1
    assert package["name"] == "team-cloud-post-ga-backlog-v0"
    assert {
        "helm_runtime_lint_ci",
        "advanced_admin_analytics",
        "memory_quality_iteration",
        "external_audit_packet",
    } <= set(items)
    assert all(item["ga_blocker"] is False for item in items.values())
    assert package["acceptance_thresholds"]["ga_blocking_items"] == 0
    assert package["exit_decision"] == "non_blocking_post_ga"
    assert signoff["gate"] == "ga"
    assert signoff["m5_final_signoff"] == "signed"
    assert all(item["status"] == "signed_for_ga" for item in signoff["signoffs"])
    assert {"final_regression", "deployment_smoke", "legal_compliance", "post_ga_backlog"} <= evidence


def test_post_ga_backlog_artifact_script_docs_and_smoke_are_registered():
    from team_cloud.post_ga_backlog import build_post_ga_backlog_package

    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    doc = DOC.read_text(encoding="utf-8")
    script = SCRIPT.read_text(encoding="utf-8")
    smoke = SMOKE_SCRIPT.read_text(encoding="utf-8")
    matrix = json.loads(SMOKE_MATRIX.read_text(encoding="utf-8"))
    domains = {entry["domain"] for entry in matrix["checks"]}

    assert artifact == build_post_ga_backlog_package()
    assert os.access(SCRIPT, os.X_OK)
    assert "team-cloud-post-ga-backlog-v0.json" in script
    assert "Post-GA backlog" in doc
    assert "non-blocking" in doc
    assert "M5 GA Sign-off" in doc
    assert "tests/team_cloud/test_post_ga_backlog.py" in smoke
    assert "post_ga_backlog" in domains
