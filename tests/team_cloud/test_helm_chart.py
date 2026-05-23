from __future__ import annotations

from pathlib import Path

import yaml


CHART_DIR = Path("deploy/team-cloud/helm/hermes-team-cloud")
CHART_YAML = CHART_DIR / "Chart.yaml"
VALUES_YAML = CHART_DIR / "values.yaml"
TEMPLATES_DIR = CHART_DIR / "templates"
DOC_PATH = Path("teamDoc/GADoc/P4-02-helm-chart.md")
FOUNDATION_SMOKE = Path("scripts/team-cloud-foundation-smoke.sh")


def _read_template(name: str) -> str:
    return (TEMPLATES_DIR / name).read_text(encoding="utf-8")


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_helm_chart_metadata_and_values_cover_required_surfaces():
    chart = _load_yaml(CHART_YAML)
    values = _load_yaml(VALUES_YAML)

    assert chart["apiVersion"] == "v2"
    assert chart["name"] == "hermes-team-cloud"
    assert chart["type"] == "application"
    assert chart["version"]
    assert chart["appVersion"]

    assert values["ingress"]["enabled"] is False
    assert values["ingress"]["tls"]["enabled"] is True
    assert values["secrets"]["create"] is True
    assert values["secrets"]["existingSecret"] == ""
    assert values["persistence"]["enabled"] is True
    assert values["persistence"]["backup"]["mountPath"] == "/backups"

    for job_name in ("migrations", "spicedbSchema", "minioBuckets"):
        assert values["jobs"][job_name]["enabled"] is True

    for image_name in ("api", "worker", "web", "postgres", "spicedb", "minio"):
        image = values["images"][image_name]
        assert image["repository"]
        assert image["tag"]
        assert image["tag"] != "latest"


def test_helm_chart_templates_include_secrets_ingress_persistence_and_jobs():
    expected_templates = {
        "secret.yaml",
        "configmap.yaml",
        "pvc.yaml",
        "deployment-api.yaml",
        "deployment-worker.yaml",
        "deployment-web.yaml",
        "service-api.yaml",
        "service-web.yaml",
        "ingress.yaml",
        "job-migrate.yaml",
        "job-spicedb-schema.yaml",
        "job-minio-buckets.yaml",
    }
    assert expected_templates <= {path.name for path in TEMPLATES_DIR.iterdir()}

    secret_template = _read_template("secret.yaml")
    assert "TEAM_CLOUD_DATABASE_URL" in secret_template
    assert "TEAM_CLOUD_SPICEDB_PRESHARED_KEY" in secret_template
    assert "TEAM_CLOUD_MINIO_SECRET_KEY" in secret_template
    assert "existingSecret" in secret_template

    api_template = _read_template("deployment-api.yaml")
    assert "secretKeyRef" in api_template
    assert "readinessProbe" in api_template
    assert "livenessProbe" in api_template
    assert "backup-storage" in api_template

    worker_template = _read_template("deployment-worker.yaml")
    assert "TEAM_CLOUD_BACKUP_MOUNT_PATH" in worker_template
    assert "backup-storage" in worker_template

    ingress_template = _read_template("ingress.yaml")
    assert "networking.k8s.io/v1" in ingress_template
    assert "tls:" in ingress_template
    assert "ingressClassName" in ingress_template

    pvc_template = _read_template("pvc.yaml")
    assert "PersistentVolumeClaim" in pvc_template
    assert "backup-storage" in pvc_template

    for job_template in (
        "job-migrate.yaml",
        "job-spicedb-schema.yaml",
        "job-minio-buckets.yaml",
    ):
        content = _read_template(job_template)
        assert "kind: Job" in content
        assert "helm.sh/hook" in content
        assert "ttlSecondsAfterFinished" in content


def test_helm_chart_is_documented_and_registered_in_smoke():
    doc = DOC_PATH.read_text(encoding="utf-8")
    smoke = FOUNDATION_SMOKE.read_text(encoding="utf-8")

    assert "deploy/team-cloud/helm/hermes-team-cloud" in doc
    assert "values.yaml" in doc
    assert "ingress" in doc
    assert "persistence" in doc
    assert "tests/team_cloud/test_helm_chart.py" in smoke
