"""Security test suite catalog for Team Cloud Beta validation."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


_CASES: tuple[dict[str, Any], ...] = (
    {
        "id": "forged_casdoor_token",
        "severity": "critical",
        "control": "jwt_middleware",
        "expected_result": "deny",
        "required_controls": ["jwks_signature_verification", "token_redaction"],
        "run_command": "scripts/run_tests.sh tests/team_cloud/test_platform_security_negative.py::test_forged_bearer_token_is_rejected_without_token_leakage",
    },
    {
        "id": "wrong_audience_issuer",
        "severity": "critical",
        "control": "jwt_middleware",
        "expected_result": "deny",
        "required_controls": ["issuer_check", "audience_check", "expiry_check"],
        "run_command": "scripts/run_tests.sh tests/team_cloud/test_jwt_middleware.py",
    },
    {
        "id": "disabled_member_access",
        "severity": "critical",
        "control": "member_status_resolver",
        "expected_result": "deny",
        "required_controls": ["member_active_check", "fail_closed"],
        "run_command": "scripts/run_tests.sh tests/team_cloud/test_platform_security_negative.py::test_disabled_member_cannot_reach_protected_api",
    },
    {
        "id": "cross_org_memory_query",
        "severity": "critical",
        "control": "memory_prefetch_authz",
        "expected_result": "deny",
        "required_controls": [
            "org_scope_filter",
            "spicedb_memory_read_check",
            "context_fencing",
        ],
        "run_command": "scripts/run_tests.sh tests/team_cloud/test_isolation_suite.py",
    },
    {
        "id": "prompt_injection_personal_memory_exfiltration",
        "severity": "high",
        "control": "memory_context_fencing",
        "expected_result": "deny",
        "required_controls": [
            "context_fencing",
            "personal_memory_scope_check",
            "tool_policy_gate",
        ],
        "run_command": "scripts/run_tests.sh tests/team_cloud/test_team_memory_provider.py tests/team_cloud/test_isolation_suite.py",
    },
    {
        "id": "tool_bypass_high_risk",
        "severity": "critical",
        "control": "team_tool_policy_hook",
        "expected_result": "deny",
        "required_controls": [
            "spicedb_tool_permission",
            "approval_required",
            "fail_closed",
        ],
        "run_command": "scripts/run_tests.sh tests/team_cloud/test_team_tool_policy_hook.py tests/team_cloud/test_tool_audit.py",
    },
    {
        "id": "break_glass_abuse",
        "severity": "high",
        "control": "break_glass_service",
        "expected_result": "deny",
        "required_controls": [
            "two_person_approval",
            "short_lived_grant",
            "audit_notification",
        ],
        "run_command": "scripts/run_tests.sh tests/team_cloud/test_break_glass.py",
    },
    {
        "id": "minio_signed_url_cross_org",
        "severity": "high",
        "control": "object_manifest_owner_check",
        "expected_result": "deny",
        "required_controls": [
            "org_id_match",
            "owner_member_match",
            "checksum_validation",
        ],
        "run_command": "scripts/run_tests.sh tests/team_cloud/test_backup_storage.py tests/team_cloud/test_minio_manifest.py",
    },
)


def build_security_test_suite() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "name": "team-cloud-security-suite-v0",
        "scope": "P4 beta negative security validation",
        "exit_criteria": {
            "critical_cases_failed": 0,
            "high_cases_failed": 0,
            "token_leakage_allowed": False,
            "cross_org_data_access_allowed": False,
        },
        "cases": deepcopy(list(_CASES)),
    }


__all__ = ["build_security_test_suite"]
