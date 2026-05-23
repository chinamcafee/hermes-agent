from __future__ import annotations

import json
import os
from pathlib import Path


ARTIFACT = Path("teamDoc/GADoc/artifacts/pilot/team-cloud-pilot-onboarding-v0.json")
DOC = Path("teamDoc/GADoc/P4-10-pilot-onboarding.md")
SCRIPT = Path("scripts/team-cloud-pilot-onboarding.py")
SMOKE_SCRIPT = Path("scripts/team-cloud-foundation-smoke.sh")
SMOKE_MATRIX = Path("teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json")


def test_pilot_onboarding_plan_covers_three_teams_gateways_and_two_week_run():
    from team_cloud.pilot import build_pilot_onboarding_plan

    plan = build_pilot_onboarding_plan()

    assert plan["schema_version"] == 1
    assert plan["name"] == "team-cloud-pilot-onboarding-v0"
    assert len(plan["pilot_teams"]) == 3
    assert {team["gateway_platform"] for team in plan["pilot_teams"]} == {
        "slack",
        "telegram",
        "api_server",
    }
    assert all(team["initial_projects"] for team in plan["pilot_teams"])
    assert all(team["member_import"]["source"] == "casdoor_group" for team in plan["pilot_teams"])
    assert plan["schedule"]["duration_days"] == 14
    assert plan["feedback"]["cadence"] == "weekly"
    assert "usage" in plan["weekly_review"]["signals"]
    assert "security_events" in plan["weekly_review"]["signals"]


def test_pilot_onboarding_artifact_script_docs_and_smoke_are_registered():
    from team_cloud.pilot import build_pilot_onboarding_plan

    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    doc = DOC.read_text(encoding="utf-8")
    script = SCRIPT.read_text(encoding="utf-8")
    smoke = SMOKE_SCRIPT.read_text(encoding="utf-8")
    matrix = json.loads(SMOKE_MATRIX.read_text(encoding="utf-8"))
    domains = {entry["domain"] for entry in matrix["checks"]}

    assert artifact == build_pilot_onboarding_plan()
    assert os.access(SCRIPT, os.X_OK)
    assert "team-cloud-pilot-onboarding-v0.json" in script
    assert "pilot_teams" in doc
    assert "feedback" in doc
    assert "tests/team_cloud/test_pilot_onboarding.py" in smoke
    assert "pilot_onboarding" in domains
