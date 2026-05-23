from __future__ import annotations

import json
import os
from pathlib import Path


ARTIFACT = Path("teamDoc/GADoc/artifacts/usage/team-cloud-cost-quotas-v0.json")
DOC = Path("teamDoc/GADoc/P4-12-cost-quotas-tuning.md")
SCRIPT = Path("scripts/team-cloud-cost-quotas.py")
SMOKE_SCRIPT = Path("scripts/team-cloud-foundation-smoke.sh")
SMOKE_MATRIX = Path("teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json")


def test_cost_quota_tuning_defines_defaults_alerts_and_dashboard_signals():
    from team_cloud.usage import build_cost_quota_tuning

    tuning = build_cost_quota_tuning()

    assert tuning["schema_version"] == 1
    assert tuning["name"] == "team-cloud-cost-quotas-v0"
    assert tuning["default_quotas"]["run_count"] > 0
    assert tuning["default_quotas"]["token_count"] > tuning["default_quotas"]["run_count"]
    assert tuning["alert_thresholds"]["warning_ratio"] == 0.8
    assert tuning["alert_thresholds"]["critical_ratio"] == 0.95
    assert "run_count" in tuning["dashboard_signals"]
    assert "backup_size_bytes" in tuning["dashboard_signals"]
    assert "quota_exceeded" in tuning["limit_alerts"]


def test_cost_quota_artifact_script_docs_and_smoke_are_registered():
    from team_cloud.usage import build_cost_quota_tuning

    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    doc = DOC.read_text(encoding="utf-8")
    script = SCRIPT.read_text(encoding="utf-8")
    smoke = SMOKE_SCRIPT.read_text(encoding="utf-8")
    matrix = json.loads(SMOKE_MATRIX.read_text(encoding="utf-8"))
    domains = {entry["domain"] for entry in matrix["checks"]}

    assert artifact == build_cost_quota_tuning()
    assert os.access(SCRIPT, os.X_OK)
    assert "team-cloud-cost-quotas-v0.json" in script
    assert "default_quotas" in doc
    assert "limit_alerts" in doc
    assert "tests/team_cloud/test_cost_quota_tuning.py" in smoke
    assert "cost_quota_tuning" in domains
