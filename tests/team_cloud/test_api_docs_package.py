from __future__ import annotations

import json
import os
from pathlib import Path


ARTIFACT = Path("teamDoc/GADoc/artifacts/release/team-cloud-api-docs-v0.json")
DOC = Path("teamDoc/GADoc/P5-05-api-docs.md")
SCRIPT = Path("scripts/team-cloud-api-docs.py")
SMOKE_SCRIPT = Path("scripts/team-cloud-foundation-smoke.sh")
SMOKE_MATRIX = Path("teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json")


def test_api_docs_cover_team_memory_authz_backup_audit_and_examples():
    from team_cloud.api_docs import build_api_docs_package

    package = build_api_docs_package()
    section_ids = {section["id"] for section in package["sections"]}
    endpoints = {(endpoint["method"], endpoint["path"]) for endpoint in package["endpoints"]}
    examples = {example["id"] for example in package["examples"]}
    error_codes = {error["status"] for error in package["error_model"]}

    assert package["schema_version"] == 1
    assert package["name"] == "team-cloud-api-docs-v0"
    assert {
        "platform_health",
        "identity_auth",
        "admin_api",
        "chat_sessions_api",
        "memory_api",
        "memory_review_api",
        "authz_api",
        "backup_policy_api",
        "audit_usage_notifications_api",
    } <= section_ids
    assert {
        ("GET", "/healthz"),
        ("GET", "/readyz"),
        ("GET", "/metrics"),
        ("GET", "/auth/oidc/authorize"),
        ("GET", "/api/whoami"),
        ("GET", "/api/authz/explain"),
        ("POST", "/api/organizations"),
        ("POST", "/api/chat/runs"),
        ("GET", "/api/cloud/sessions"),
        ("POST", "/v1/memory"),
        ("POST", "/v1/memory/prefetch"),
        ("GET", "/v1/memory/review"),
        ("GET", "/v1/me/memory-backup-policy"),
        ("GET", "/api/audit/events"),
        ("GET", "/api/usage/orgs/{org_id}/summary"),
        ("GET", "/api/notifications"),
    } <= endpoints
    assert {"curl_create_org", "python_prefetch_memory", "service_account_chat_run"} <= examples
    assert {400, 401, 403, 404, 409, 429} <= error_codes


def test_api_docs_artifact_script_docs_and_smoke_are_registered():
    from team_cloud.api_docs import build_api_docs_package

    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    doc = DOC.read_text(encoding="utf-8")
    script = SCRIPT.read_text(encoding="utf-8")
    smoke = SMOKE_SCRIPT.read_text(encoding="utf-8")
    matrix = json.loads(SMOKE_MATRIX.read_text(encoding="utf-8"))
    domains = {entry["domain"] for entry in matrix["checks"]}

    assert artifact == build_api_docs_package()
    assert os.access(SCRIPT, os.X_OK)
    assert "team-cloud-api-docs-v0.json" in script
    assert "Team API" in doc
    assert "Memory API" in doc
    assert "AuthZ API" in doc
    assert "POST /api/chat/runs" in doc
    assert "POST /v1/memory/prefetch" in doc
    assert "tests/team_cloud/test_api_docs_package.py" in smoke
    assert "api_docs" in domains
