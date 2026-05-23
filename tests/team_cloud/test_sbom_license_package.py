from __future__ import annotations

import json
import os
from pathlib import Path


ARTIFACT = Path("teamDoc/GADoc/artifacts/release/team-cloud-sbom-license-v0.json")
DOC = Path("teamDoc/GADoc/P5-02-sbom-license-package.md")
SCRIPT = Path("scripts/team-cloud-sbom-license.py")
SMOKE_SCRIPT = Path("scripts/team-cloud-foundation-smoke.sh")
SMOKE_MATRIX = Path("teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json")


def test_sbom_license_package_covers_core_components_and_minio_agpl_obligations():
    from team_cloud.sbom_license import build_sbom_license_package

    package = build_sbom_license_package()
    components = {item["name"]: item for item in package["components"]}
    risk_closures = {item["id"]: item["status"] for item in package["risk_closures"]}

    assert package["schema_version"] == 1
    assert package["name"] == "team-cloud-sbom-license-v0"
    assert package["sbom_format"] == "cyclonedx-json"
    assert {"Casdoor", "SpiceDB", "PostgreSQL", "pgvector", "MinIO"} <= set(components)
    assert components["MinIO"]["license"] == "AGPL-3.0"
    assert components["MinIO"]["version"] == "RELEASE.2025-09-07T16-13-09Z"
    assert "source_offer_required" in package["minio_agpl_notice"]["obligations"]
    assert "s3_compatible_replacement_path" in package["minio_agpl_notice"]
    assert "MinIO" in package["license_report"]["agpl_components"]
    assert "psycopg" in package["license_report"]["lgpl_non_default_components"]
    assert risk_closures["RISK-001"] == "closed"
    assert risk_closures["RISK-002"] == "closed"
    assert risk_closures["RISK-012"] == "closed"


def test_sbom_license_artifact_script_docs_and_smoke_are_registered():
    from team_cloud.sbom_license import build_sbom_license_package

    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    doc = DOC.read_text(encoding="utf-8")
    script = SCRIPT.read_text(encoding="utf-8")
    smoke = SMOKE_SCRIPT.read_text(encoding="utf-8")
    matrix = json.loads(SMOKE_MATRIX.read_text(encoding="utf-8"))
    domains = {entry["domain"] for entry in matrix["checks"]}

    assert artifact == build_sbom_license_package()
    assert os.access(SCRIPT, os.X_OK)
    assert "team-cloud-sbom-license-v0.json" in script
    assert "MinIO AGPL-3.0" in doc
    assert "license_report" in doc
    assert "risk_closures" in doc
    assert "tests/team_cloud/test_sbom_license_package.py" in smoke
    assert "sbom_license_package" in domains
