from __future__ import annotations

from pathlib import Path

import yaml


COMPOSE_PATH = Path("deploy/team-cloud/compose.yaml")
MANIFEST_PATH = Path("deploy/team-cloud/offline/manifest.yaml")
BUNDLE_SCRIPT = Path("scripts/team-cloud-offline-bundle.sh")
INSTALL_SCRIPT = Path("deploy/team-cloud/offline/install.sh")
README_PATH = Path("deploy/team-cloud/offline/README.md")
DOC_PATH = Path("teamDoc/GADoc/P4-03-offline-bundle.md")
FOUNDATION_SMOKE = Path("scripts/team-cloud-foundation-smoke.sh")


def _default_image_ref(image_value: str) -> str:
    if image_value.startswith("${") and ":-" in image_value and image_value.endswith("}"):
        return image_value.removesuffix("}").split(":-", 1)[1]
    return image_value


def test_offline_bundle_manifest_lists_images_charts_checksums_and_scripts():
    manifest = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))

    assert manifest["schema_version"] == 1
    assert manifest["bundle_name"] == "hermes-team-cloud-offline"
    assert manifest["chart"]["path"] == "deploy/team-cloud/helm/hermes-team-cloud"
    assert manifest["chart"]["archive"] == "charts/hermes-team-cloud-0.1.0.tgz"
    assert manifest["checksums"]["algorithm"] == "sha256"
    assert manifest["checksums"]["file"] == "SHA256SUMS"
    assert manifest["install_script"] == "install.sh"

    image_refs = {image["ref"] for image in manifest["images"]}
    assert {
        "hermes-team-api:dev",
        "hermes-team-worker:dev",
        "hermes-team-runtime:dev",
        "nginx:1.29.3-alpine",
        "alpine:3.22.2",
        "pgvector/pgvector:0.8.2-pg18-trixie",
        "ghcr.io/authzed/spicedb:v1.53.0-debug",
        "ghcr.io/authzed/zed:v1.1.1-debug",
        "minio/minio:RELEASE.2025-09-07T16-13-09Z",
        "minio/mc:RELEASE.2025-08-13T08-35-41Z",
        "casbin/casdoor:3.60.1",
        "axllent/mailpit:v1.29.5",
    } <= image_refs


def test_offline_bundle_manifest_covers_compose_default_images():
    compose = yaml.safe_load(COMPOSE_PATH.read_text(encoding="utf-8"))
    manifest = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))

    compose_refs = {
        _default_image_ref(service["image"])
        for service in compose["services"].values()
        if service.get("image")
    }
    manifest_refs = {image["ref"] for image in manifest["images"]}

    assert compose_refs <= manifest_refs


def test_offline_bundle_scripts_verify_checksums_and_install_chart():
    bundle_script = BUNDLE_SCRIPT.read_text(encoding="utf-8")
    install_script = INSTALL_SCRIPT.read_text(encoding="utf-8")

    assert "helm package" in bundle_script
    assert "docker save" in bundle_script
    assert "sha256sum" in bundle_script
    assert "manifest.yaml" in bundle_script
    assert "images.txt" in bundle_script
    assert "yaml.safe_load" in bundle_script
    assert "image[\"ref\"]" in bundle_script

    assert "sha256sum -c SHA256SUMS" in install_script
    assert "docker load" in install_script
    assert "helm upgrade --install" in install_script
    assert "charts/hermes-team-cloud-0.1.0.tgz" in install_script


def test_offline_bundle_docs_and_smoke_registration_are_present():
    readme = README_PATH.read_text(encoding="utf-8")
    doc = DOC_PATH.read_text(encoding="utf-8")
    smoke = FOUNDATION_SMOKE.read_text(encoding="utf-8")

    assert "air-gapped" in readme
    assert "SHA256SUMS" in readme
    assert "docker load" in readme
    assert "helm upgrade --install" in readme
    assert "deploy/team-cloud/offline/manifest.yaml" in doc
    assert "scripts/team-cloud-offline-bundle.sh" in doc
    assert "tests/team_cloud/test_offline_bundle.py" in smoke
