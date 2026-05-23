from __future__ import annotations

import json
from pathlib import Path


DASHBOARD_PATH = Path(
    "teamDoc/GADoc/artifacts/observability/team-cloud-grafana-dashboard-v0.json"
)
DOC_PATH = Path("teamDoc/GADoc/P4-04-metrics-dashboard.md")
FOUNDATION_SMOKE = Path("scripts/team-cloud-foundation-smoke.sh")

REQUIRED_METRICS = {
    "team_cloud_http_requests_total",
    "team_cloud_spicedb_check_latency_ms",
    "team_cloud_spicedb_denies_total",
    "team_cloud_pgvector_query_latency_ms",
    "team_cloud_minio_operation_latency_ms",
    "team_cloud_worker_lag_seconds",
    "team_cloud_audit_events_total",
}

REQUIRED_PANELS = {
    "Team API",
    "SpiceDB AuthZ",
    "PostgreSQL pgvector",
    "MinIO Object Storage",
    "Workers",
    "Audit and Security",
}


def test_observability_metrics_catalog_covers_beta_dashboard_domains():
    from team_cloud.observability import METRICS_CATALOG

    metric_names = {metric["name"] for metric in METRICS_CATALOG}
    assert REQUIRED_METRICS <= metric_names

    domains = {metric["domain"] for metric in METRICS_CATALOG}
    assert {
        "team_api",
        "spicedb",
        "pgvector",
        "minio",
        "worker",
        "audit_security",
    } <= domains


def test_grafana_dashboard_artifact_contains_required_panels_and_queries():
    dashboard = json.loads(DASHBOARD_PATH.read_text(encoding="utf-8"))
    payload = json.dumps(dashboard, sort_keys=True)

    assert dashboard["title"] == "Hermes Team Cloud GA"
    panel_titles = {panel["title"] for panel in dashboard["panels"]}
    assert REQUIRED_PANELS <= panel_titles

    for metric in REQUIRED_METRICS:
        assert metric in payload


def test_metrics_dashboard_docs_and_smoke_registration_are_present():
    doc = DOC_PATH.read_text(encoding="utf-8")
    smoke = FOUNDATION_SMOKE.read_text(encoding="utf-8")

    assert "team-cloud-grafana-dashboard-v0.json" in doc
    assert "SpiceDB" in doc
    assert "pgvector" in doc
    assert "MinIO" in doc
    assert "worker lag" in doc
    assert "tests/team_cloud/test_metrics_dashboard.py" in smoke
