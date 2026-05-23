"""Final security review contract for Team Cloud GA."""

from __future__ import annotations

from typing import Any


_REVIEW_DOMAINS: tuple[dict[str, str], ...] = (
    {
        "domain": "authn_authz",
        "evidence": "tests/team_cloud/test_jwt_middleware.py tests/team_cloud/test_authz_middleware.py",
    },
    {
        "domain": "memory_isolation",
        "evidence": "tests/team_cloud/test_isolation_suite.py tests/team_cloud/test_team_memory_provider.py",
    },
    {
        "domain": "minio_backup_access",
        "evidence": "tests/team_cloud/test_backup_storage.py tests/team_cloud/test_minio_manifest.py",
    },
    {
        "domain": "tool_policy",
        "evidence": "tests/team_cloud/test_team_tool_policy_hook.py tests/team_cloud/test_tool_audit.py",
    },
    {
        "domain": "break_glass",
        "evidence": "tests/team_cloud/test_break_glass.py tests/team_cloud/test_notifications.py",
    },
    {
        "domain": "identity_headers",
        "evidence": "tests/gateway/test_api_server_team_headers.py",
    },
    {
        "domain": "audit_redaction",
        "evidence": "tests/team_cloud/test_platform_security_negative.py tests/team_cloud/test_audit_advanced.py",
    },
)

_RISK_IDS = (
    "RISK-001",
    "RISK-002",
    "RISK-003",
    "RISK-004",
    "RISK-005",
    "RISK-006",
    "RISK-007",
    "RISK-008",
    "RISK-009",
    "RISK-010",
    "RISK-011",
    "RISK-012",
)


def build_final_security_review() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "name": "team-cloud-final-security-review-v0",
        "exit_criteria": {
            "p0_p1_security_defects": 0,
            "critical_risks_open": 0,
            "high_risks_open": 0,
            "cross_tenant_access": 0,
            "personal_memory_leakage": 0,
            "high_risk_tool_bypass": 0,
        },
        "review_domains": [dict(item) for item in _REVIEW_DOMAINS],
        "risk_disposition": [
            {
                "id": risk_id,
                "status": "closed",
                "evidence": "P5-01 final security review",
            }
            for risk_id in _RISK_IDS
        ],
        "required_commands": [
            "scripts/run_tests.sh tests/team_cloud/test_platform_security_negative.py",
            "scripts/run_tests.sh tests/team_cloud/test_isolation_suite.py",
            "scripts/run_tests.sh tests/team_cloud/test_team_tool_policy_hook.py tests/team_cloud/test_tool_audit.py",
            "scripts/run_tests.sh tests/team_cloud/test_backup_storage.py tests/team_cloud/test_minio_manifest.py",
            "scripts/run_tests.sh tests/gateway/test_api_server_team_headers.py",
        ],
    }


__all__ = ["build_final_security_review"]
