from __future__ import annotations

import json
from pathlib import Path


ARTIFACT = Path("teamDoc/GADoc/artifacts/tool-risk-taxonomy-v0.json")


def test_tool_risk_taxonomy_defines_required_categories_and_approval_gate():
    from team_cloud.tool_risk import (
        RISK_CATEGORIES,
        classify_tool_call,
        risk_requires_approval,
    )

    assert RISK_CATEGORIES == (
        "safe",
        "network",
        "file",
        "terminal",
        "destructive",
        "secret",
    )
    assert risk_requires_approval("safe") is False
    assert risk_requires_approval("network") is False
    assert risk_requires_approval("file") is False
    assert risk_requires_approval("terminal") is True
    assert risk_requires_approval("destructive") is True
    assert risk_requires_approval("secret") is True

    assert classify_tool_call("memory", {}) == "safe"
    assert classify_tool_call("web_search", {}) == "network"
    assert classify_tool_call("read_file", {"path": "README.md"}) == "file"
    assert classify_tool_call("patch", {"path": "app.py"}) == "file"
    assert classify_tool_call("terminal", {"command": "pytest"}) == "terminal"
    assert classify_tool_call("terminal", {"command": "rm -rf /tmp/hermes"}) == "destructive"
    assert classify_tool_call("send_message", {"token": "secret"}) == "secret"


def test_tool_risk_taxonomy_artifact_matches_builder():
    from team_cloud.tool_risk import build_tool_risk_taxonomy

    built = build_tool_risk_taxonomy()
    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))

    assert artifact["schema_version"] == 1
    assert artifact["name"] == "tool-risk-taxonomy-v0"
    assert artifact["categories"] == list(built["categories"])
    assert artifact["tool_defaults"] == built["tool_defaults"]
    assert artifact["approval_required"] == ["terminal", "destructive", "secret"]


def test_tool_risk_taxonomy_docs_and_smoke_are_registered():
    doc = Path("teamDoc/GADoc/P3-01-tool-risk-taxonomy.md").read_text(encoding="utf-8")
    smoke = Path("scripts/team-cloud-foundation-smoke.sh").read_text(encoding="utf-8")

    assert "safe/network/file/terminal/destructive/secret" in doc
    assert "TeamToolPolicyHook" in doc
    assert "tool-risk-taxonomy-v0.json" in doc
    assert "tests/team_cloud/test_tool_risk_taxonomy.py" in smoke
