from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient


class FakeAuthzClient:
    def __init__(self, *, allowed: bool = True, fail: bool = False):
        self.allowed = allowed
        self.fail = fail
        self.calls = []

    def check(self, **kwargs):
        self.calls.append(kwargs)
        if self.fail:
            raise RuntimeError("spicedb unavailable")
        from team_cloud.authz.spicedb import PermissionDecision

        return PermissionDecision(
            allowed=self.allowed,
            reason="allowed" if self.allowed else "denied",
            subject=kwargs["subject"],
            resource=kwargs["resource"],
            permission=kwargs.get("permission") or "run_agent",
        )


def _client(
    *,
    authz_client=None,
    outbox_pending=None,
) -> tuple[TestClient, FakeAuthzClient]:
    from team_cloud.authz.middleware import RoutePermissionRule, install_authz_middleware
    from team_cloud.authz.spicedb import SubjectRef

    app = FastAPI()

    @app.get("/api/projects/{project_id}/run")
    def run_project(project_id: str):
        return {"project_id": project_id, "cache_key": app.state.last_cache_key}

    @app.get("/api/public")
    def public():
        return {"ok": True}

    fake_authz = authz_client or FakeAuthzClient()
    install_authz_middleware(
        app,
        authz_client=fake_authz,
        route_permissions=[
            RoutePermissionRule(
                method="GET",
                path_template="/api/projects/{project_id}/run",
                resource_type="project",
                resource_id_param="project_id",
                action="chat.run",
                consistency="fully_consistent_for_sensitive",
            )
        ],
        subject_resolver=lambda request: SubjectRef("user", "alice"),
        outbox_pending=outbox_pending,
        cache_key_callback=lambda key: setattr(app.state, "last_cache_key", key),
    )
    return TestClient(app), fake_authz


def test_authz_middleware_allows_and_sets_cache_key():
    client, authz_client = _client()

    response = client.get("/api/projects/project-1/run")

    assert response.status_code == 200
    assert response.json()["project_id"] == "project-1"
    assert response.json()["cache_key"] == "user:alice|project:project-1|run_agent"
    assert authz_client.calls[-1]["subject"].as_spicedb() == "user:alice"
    assert authz_client.calls[-1]["resource"].as_spicedb() == "project:project-1"
    assert authz_client.calls[-1]["action"] == "chat.run"
    assert authz_client.calls[-1]["consistency"] == "fully_consistent_for_sensitive"


def test_authz_middleware_denies_when_spicedb_denies():
    client, _authz_client = _client(authz_client=FakeAuthzClient(allowed=False))

    response = client.get("/api/projects/project-1/run")

    assert response.status_code == 403
    assert response.json()["detail"] == "permission_denied"


def test_authz_middleware_fails_closed_on_spicedb_error():
    client, _authz_client = _client(authz_client=FakeAuthzClient(fail=True))

    response = client.get("/api/projects/project-1/run")

    assert response.status_code == 403
    assert response.json()["detail"] == "authorization_unavailable"


def test_authz_middleware_blocks_when_relationship_outbox_pending():
    client, authz_client = _client(outbox_pending=lambda resource_type, resource_id: True)

    response = client.get("/api/projects/project-1/run")

    assert response.status_code == 403
    assert response.json()["detail"] == "authorization_pending_relationship_sync"
    assert authz_client.calls == []


def test_authz_middleware_skips_unmatched_route():
    client, authz_client = _client()

    response = client.get("/api/public")

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert authz_client.calls == []
