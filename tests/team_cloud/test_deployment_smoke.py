from __future__ import annotations

import json
import os
from pathlib import Path


ARTIFACT = Path("teamDoc/GADoc/artifacts/release/team-cloud-deployment-smoke-v0.json")
DOC = Path("teamDoc/GADoc/P5-13-deployment-smoke.md")
SCRIPT = Path("scripts/team-cloud-deployment-smoke.py")
SMOKE_SCRIPT = Path("scripts/team-cloud-foundation-smoke.sh")
SMOKE_MATRIX = Path("teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json")


def test_deployment_smoke_covers_compose_helm_and_offline_bundle():
    from team_cloud.deployment_smoke import build_deployment_smoke_package

    package = build_deployment_smoke_package()
    gates = {gate["id"]: gate for gate in package["gates"]}

    assert package["schema_version"] == 1
    assert package["name"] == "team-cloud-deployment-smoke-v0"
    assert {
        "compose_smoke",
        "helm_static_smoke",
        "offline_bundle_smoke",
        "fresh_environment_smoke",
    } <= set(gates)
    assert "tests/team_cloud/test_local_compose_stack.py" in gates["compose_smoke"]["command"]
    assert "tests/team_cloud/test_compose_hardening.py" in gates["compose_smoke"]["command"]
    assert gates["helm_static_smoke"]["chart_path"] == "deploy/team-cloud/helm/hermes-team-cloud"
    assert gates["helm_static_smoke"]["helm_lint_status"] == "passed"
    assert gates["helm_static_smoke"]["helm_runtime_status"] == "passed"
    assert "config.logLevel=DEBUG" in gates["helm_static_smoke"]["helm_runtime_command"]
    assert "tests/team_cloud/test_helm_chart.py" in gates["helm_static_smoke"]["command"]
    assert gates["offline_bundle_smoke"]["manifest_path"] == "deploy/team-cloud/offline/manifest.yaml"
    assert "tests/team_cloud/test_offline_bundle.py" in gates["offline_bundle_smoke"]["command"]
    assert gates["fresh_environment_smoke"]["environment_type"] == "fresh_ga_environment"
    assert "docker compose -f deploy/team-cloud/compose.yaml config" in gates["fresh_environment_smoke"]["commands"]
    assert "scripts/team-cloud-foundation-smoke.sh" in gates["fresh_environment_smoke"]["commands"]
    assert gates["fresh_environment_smoke"]["helm_lint_status"] == "passed"

    results = {result["id"]: result for result in gates["fresh_environment_smoke"]["local_run_results"]}
    assert {
        "compose_config",
        "compose_up_wait",
        "foundation_smoke",
        "helm_lint",
        "helm_upgrade_rollback",
        "offline_install_manifest_check",
    } <= set(results)
    assert all(result["status"] == "passed" for result in results.values())
    assert "config.logLevel=DEBUG" in results["helm_upgrade_rollback"]["command"]

    assert "GA-REL-001" in package["ga_matrix_items"]
    assert "GA-REL-002" in package["ga_matrix_items"]
    assert package["acceptance_thresholds"]["failed_tests"] == 0
    assert package["exit_decision"] == "required_for_ga"


def test_deployment_smoke_artifact_script_docs_and_smoke_are_registered():
    from team_cloud.deployment_smoke import build_deployment_smoke_package

    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    doc = DOC.read_text(encoding="utf-8")
    script = SCRIPT.read_text(encoding="utf-8")
    smoke = SMOKE_SCRIPT.read_text(encoding="utf-8")
    matrix = json.loads(SMOKE_MATRIX.read_text(encoding="utf-8"))
    domains = {entry["domain"] for entry in matrix["checks"]}

    assert artifact == build_deployment_smoke_package()
    assert os.access(SCRIPT, os.X_OK)
    assert "team-cloud-deployment-smoke-v0.json" in script
    assert "Docker Compose" in doc
    assert "Helm" in doc
    assert "Offline bundle" in doc
    assert "fresh_ga_environment" in doc
    assert "GA-REL-001" in doc
    assert "GA-REL-002" in doc
    assert "helm lint" in doc
    assert "helm upgrade/rollback" in doc
    assert "compose_up_wait" in doc
    assert "foundation_smoke" in doc
    assert "tests/team_cloud/test_deployment_smoke.py" in smoke
    assert "deployment_smoke" in domains
