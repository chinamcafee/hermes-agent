from __future__ import annotations

import json
import os
from pathlib import Path


ARTIFACT = Path("teamDoc/GADoc/artifacts/pilot/team-cloud-pilot-telemetry-review-v0.json")
DOC = Path("teamDoc/GADoc/P4-17-pilot-telemetry-review.md")
SCRIPT = Path("scripts/team-cloud-pilot-telemetry-review.py")
SMOKE_SCRIPT = Path("scripts/team-cloud-foundation-smoke.sh")
SMOKE_MATRIX = Path("teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json")


def test_pilot_telemetry_review_covers_weekly_signals_and_release_gates():
    from team_cloud.telemetry_review import build_pilot_telemetry_review

    review = build_pilot_telemetry_review()

    assert review["schema_version"] == 1
    assert review["name"] == "team-cloud-pilot-telemetry-review-v0"
    assert review["period"]["duration_days"] == 14
    assert review["period"]["cadence"] == "weekly"
    assert review["pilot_source"].endswith("team-cloud-pilot-onboarding-v0.json")
    assert {
        "usage",
        "latency",
        "errors",
        "security_events",
        "backup_jobs",
        "cost_quotas",
    } <= set(review["signals"])
    assert review["release_gates"]["open_p0_p1"] == 0
    assert review["release_gates"]["cross_org_access"] == 0
    assert review["release_gates"]["personal_memory_leakage"] == 0
    assert review["release_gates"]["authz_fail_open"] == 0
    assert "weekly_report" in review["outputs"]
    assert "beta_exit_inputs" in review["outputs"]


def test_pilot_telemetry_review_artifact_script_docs_and_smoke_are_registered():
    from team_cloud.telemetry_review import build_pilot_telemetry_review

    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    doc = DOC.read_text(encoding="utf-8")
    script = SCRIPT.read_text(encoding="utf-8")
    smoke = SMOKE_SCRIPT.read_text(encoding="utf-8")
    matrix = json.loads(SMOKE_MATRIX.read_text(encoding="utf-8"))
    domains = {entry["domain"] for entry in matrix["checks"]}

    assert artifact == build_pilot_telemetry_review()
    assert os.access(SCRIPT, os.X_OK)
    assert "team-cloud-pilot-telemetry-review-v0.json" in script
    assert "security_events" in doc
    assert "release_gates" in doc
    assert "weekly_report" in doc
    assert "tests/team_cloud/test_pilot_telemetry_review.py" in smoke
    assert "pilot_telemetry_review" in domains
