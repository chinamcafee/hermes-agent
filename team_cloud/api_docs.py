"""API documentation package contract for Team Cloud GA."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


_SECTIONS: tuple[dict[str, Any], ...] = (
    {
        "id": "platform_health",
        "title": "Platform Health",
        "description": "Health, readiness, and Prometheus metrics endpoints.",
    },
    {
        "id": "identity_auth",
        "title": "Identity and Auth",
        "description": "Casdoor OIDC authorize/callback, JWT principal lookup, and identity headers.",
    },
    {
        "id": "admin_api",
        "title": "Admin API",
        "description": "Organization, team, member invite, member disable, and relationship outbox behavior.",
    },
    {
        "id": "chat_sessions_api",
        "title": "Chat and Sessions API",
        "description": "Team-scoped chat runs, cloud session history, tool calls, and runtime event ingestion.",
    },
    {
        "id": "memory_api",
        "title": "Memory API",
        "description": "Create, list, update, archive, delete, restore, observe, and prefetch memory.",
    },
    {
        "id": "memory_review_api",
        "title": "Memory Review API",
        "description": "List, approve, and reject proposed memory items and conflicts.",
    },
    {
        "id": "authz_api",
        "title": "AuthZ API",
        "description": "Permission explanation and fail-closed authorization behavior.",
    },
    {
        "id": "backup_policy_api",
        "title": "Backup Policy API",
        "description": "Member self-service memory backup policy read and update endpoints.",
    },
    {
        "id": "audit_usage_notifications_api",
        "title": "Audit, Usage, and Notifications API",
        "description": "Audit query/export, usage quota, usage summary, and notification acknowledgement.",
    },
)

_ENDPOINTS: tuple[dict[str, Any], ...] = (
    {"section": "platform_health", "method": "GET", "path": "/healthz"},
    {"section": "platform_health", "method": "GET", "path": "/readyz"},
    {"section": "platform_health", "method": "GET", "path": "/metrics"},
    {"section": "identity_auth", "method": "GET", "path": "/auth/oidc/authorize"},
    {"section": "identity_auth", "method": "GET", "path": "/auth/oidc/callback"},
    {"section": "identity_auth", "method": "GET", "path": "/api/whoami"},
    {"section": "identity_auth", "method": "POST", "path": "/v1/external-identities/resolve"},
    {"section": "authz_api", "method": "GET", "path": "/api/authz/explain"},
    {"section": "admin_api", "method": "POST", "path": "/api/organizations"},
    {"section": "admin_api", "method": "GET", "path": "/api/organizations"},
    {
        "section": "admin_api",
        "method": "POST",
        "path": "/api/organizations/{org_id}/teams",
    },
    {
        "section": "admin_api",
        "method": "GET",
        "path": "/api/organizations/{org_id}/teams",
    },
    {
        "section": "admin_api",
        "method": "GET",
        "path": "/api/organizations/{org_id}/members",
    },
    {
        "section": "admin_api",
        "method": "POST",
        "path": "/api/organizations/{org_id}/members/invite",
    },
    {
        "section": "admin_api",
        "method": "PATCH",
        "path": "/api/organizations/{org_id}/members/{member_id}/disable",
    },
    {"section": "chat_sessions_api", "method": "POST", "path": "/api/chat/runs"},
    {
        "section": "chat_sessions_api",
        "method": "GET",
        "path": "/api/chat/runs/{run_id}/events",
    },
    {"section": "chat_sessions_api", "method": "GET", "path": "/api/cloud/sessions"},
    {
        "section": "chat_sessions_api",
        "method": "GET",
        "path": "/api/cloud/sessions/{session_id}",
    },
    {
        "section": "chat_sessions_api",
        "method": "POST",
        "path": "/api/cloud/sessions/{session_id}/tool-calls",
    },
    {"section": "chat_sessions_api", "method": "POST", "path": "/api/runtime/events"},
    {"section": "memory_api", "method": "POST", "path": "/v1/memory"},
    {"section": "memory_api", "method": "GET", "path": "/v1/memory"},
    {"section": "memory_api", "method": "PATCH", "path": "/v1/memory/{memory_id}"},
    {
        "section": "memory_api",
        "method": "POST",
        "path": "/v1/memory/{memory_id}/archive",
    },
    {"section": "memory_api", "method": "DELETE", "path": "/v1/memory/{memory_id}"},
    {
        "section": "memory_api",
        "method": "POST",
        "path": "/v1/memory/{memory_id}/restore",
    },
    {"section": "memory_api", "method": "POST", "path": "/v1/memory/observations"},
    {"section": "memory_api", "method": "POST", "path": "/v1/memory/prefetch"},
    {"section": "memory_review_api", "method": "GET", "path": "/v1/memory/review"},
    {
        "section": "memory_review_api",
        "method": "POST",
        "path": "/v1/memory/review/{review_id}/approve",
    },
    {
        "section": "memory_review_api",
        "method": "POST",
        "path": "/v1/memory/review/{review_id}/reject",
    },
    {
        "section": "backup_policy_api",
        "method": "GET",
        "path": "/v1/me/memory-backup-policy",
    },
    {
        "section": "backup_policy_api",
        "method": "PUT",
        "path": "/v1/me/memory-backup-policy",
    },
    {
        "section": "audit_usage_notifications_api",
        "method": "GET",
        "path": "/api/usage/orgs/{org_id}/summary",
    },
    {
        "section": "audit_usage_notifications_api",
        "method": "GET",
        "path": "/api/usage/orgs/{org_id}/quotas",
    },
    {
        "section": "audit_usage_notifications_api",
        "method": "PUT",
        "path": "/api/usage/orgs/{org_id}/quotas",
    },
    {"section": "audit_usage_notifications_api", "method": "GET", "path": "/api/notifications"},
    {
        "section": "audit_usage_notifications_api",
        "method": "POST",
        "path": "/api/notifications/{notification_id}/ack",
    },
    {"section": "audit_usage_notifications_api", "method": "GET", "path": "/api/audit/events"},
    {
        "section": "audit_usage_notifications_api",
        "method": "GET",
        "path": "/api/audit/sensitive-reads",
    },
    {
        "section": "audit_usage_notifications_api",
        "method": "GET",
        "path": "/api/audit/high-risk-tools",
    },
    {"section": "audit_usage_notifications_api", "method": "GET", "path": "/api/audit/export"},
)

_EXAMPLES: tuple[dict[str, str], ...] = (
    {
        "id": "curl_create_org",
        "language": "curl",
        "snippet": "curl -X POST $TEAM_CLOUD_URL/api/organizations -d '{\"slug\":\"acme\",\"name\":\"Acme\"}'",
    },
    {
        "id": "python_prefetch_memory",
        "language": "python",
        "snippet": "client.post('/v1/memory/prefetch', json={'org_id': 'org-1', 'member_id': 'alice', 'team_id': 'team-1', 'query': 'roadmap'})",
    },
    {
        "id": "service_account_chat_run",
        "language": "curl",
        "snippet": "curl -X POST $TEAM_CLOUD_URL/api/chat/runs -H 'Authorization: Bearer <token>' -d @run.json",
    },
)

_ERROR_MODEL: tuple[dict[str, Any], ...] = (
    {"status": 400, "detail": "invalid_request or <field>_required"},
    {"status": 401, "detail": "missing_principal"},
    {"status": 403, "detail": "permission_denied or authorization_unavailable"},
    {"status": 404, "detail": "resource_not_found"},
    {"status": 409, "detail": "review item state conflict"},
    {"status": 429, "detail": "quota_exceeded"},
)


def build_api_docs_package() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "name": "team-cloud-api-docs-v0",
        "auth": {
            "identity_provider": "Casdoor",
            "primary": "Casdoor JWT",
            "automation": "scoped PAT or service account token",
            "authorization": "SpiceDB fail-closed checks for protected routes",
        },
        "sections": deepcopy(list(_SECTIONS)),
        "endpoints": deepcopy(list(_ENDPOINTS)),
        "examples": deepcopy(list(_EXAMPLES)),
        "error_model": deepcopy(list(_ERROR_MODEL)),
        "verification": [
            "scripts/run_tests.sh tests/team_cloud/test_api_docs_package.py",
            "scripts/team-cloud-foundation-smoke.sh",
        ],
    }


__all__ = ["build_api_docs_package"]
