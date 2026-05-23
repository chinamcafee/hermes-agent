from __future__ import annotations

from fastapi.testclient import TestClient


def test_metrics_endpoint_exports_request_counts_and_structured_events():
    from team_cloud.api import create_app

    client = TestClient(create_app(oidc_client=object()))

    health = client.get("/healthz", headers={"x-request-id": "req-observe-1"})
    metrics = client.get("/metrics")

    assert health.status_code == 200
    assert metrics.status_code == 200
    assert metrics.headers["content-type"].startswith("text/plain")
    assert (
        'team_cloud_http_requests_total{method="GET",path="/healthz",status="200"} 1'
        in metrics.text
    )

    health_events = [
        event
        for event in client.app.state.observability.events
        if event["path"] == "/healthz"
    ]
    assert health_events[-1]["request_id"] == "req-observe-1"
    assert health_events[-1]["method"] == "GET"
    assert health_events[-1]["status_code"] == 200
    assert health_events[-1]["duration_ms"] >= 0


def test_readyz_keeps_dependency_check_shape_for_observability():
    from team_cloud.api import create_app

    client = TestClient(create_app(oidc_client=object()))

    response = client.get("/readyz")

    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "team-cloud-api"
    assert "config" in payload["checks"]
    assert "migrations" in payload["checks"]
