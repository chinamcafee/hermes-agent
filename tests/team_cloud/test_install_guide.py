from __future__ import annotations

import json
import os
from pathlib import Path


ARTIFACT = Path("teamDoc/GADoc/artifacts/release/team-cloud-install-guide-v0.json")
DOC = Path("teamDoc/GADoc/P5-03-install-guide.md")
SCRIPT = Path("scripts/team-cloud-install-guide.py")
SMOKE_SCRIPT = Path("scripts/team-cloud-foundation-smoke.sh")
SMOKE_MATRIX = Path("teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json")


def test_install_guide_covers_compose_helm_offline_preflight_and_first_login():
    from team_cloud.install_guide import build_install_guide_package

    guide = build_install_guide_package()
    install_paths = {item["id"]: item for item in guide["install_paths"]}

    assert guide["schema_version"] == 1
    assert guide["name"] == "team-cloud-install-guide-v0"
    assert {"compose", "helm", "offline_bundle"} <= set(install_paths)
    assert install_paths["compose"]["entrypoint"] == "deploy/team-cloud/compose.yaml"
    assert install_paths["helm"]["entrypoint"].endswith("Chart.yaml")
    assert "checksums" in install_paths["offline_bundle"]["required_artifacts"]
    assert {"python_3_11", "container_runtime", "ports_available", "secrets_present"} <= set(
        guide["preflight_checks"]
    )
    assert guide["first_login"]["identity_provider"] == "Casdoor"
    assert "owner_bootstrap" in guide["first_login"]["steps"]
    assert {"team_api", "casdoor", "spicedb", "postgres", "minio"} <= set(
        guide["health_checks"]
    )
    assert "spicedb_schema_load_failure" in guide["troubleshooting"]


def test_install_guide_artifact_script_docs_and_smoke_are_registered():
    from team_cloud.install_guide import build_install_guide_package

    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    doc = DOC.read_text(encoding="utf-8")
    script = SCRIPT.read_text(encoding="utf-8")
    smoke = SMOKE_SCRIPT.read_text(encoding="utf-8")
    matrix = json.loads(SMOKE_MATRIX.read_text(encoding="utf-8"))
    domains = {entry["domain"] for entry in matrix["checks"]}

    assert artifact == build_install_guide_package()
    assert os.access(SCRIPT, os.X_OK)
    assert "team-cloud-install-guide-v0.json" in script
    assert "compose" in doc
    assert "helm" in doc
    assert "offline_bundle" in doc
    assert "first_login" in doc
    assert "tests/team_cloud/test_install_guide.py" in smoke
    assert "install_guide" in domains
