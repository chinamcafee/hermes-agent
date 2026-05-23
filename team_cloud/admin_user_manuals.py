"""Admin and user manual package contract for Team Cloud GA."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


_MANUALS: tuple[dict[str, Any], ...] = (
    {
        "id": "admin",
        "title": "Team Cloud Administrator Manual",
        "audience": "Org Owner and Team Admin",
        "sections": [
            {
                "id": "organization_setup",
                "summary": "Create organizations, freeze slugs, configure Casdoor identity, and confirm initial SpiceDB relationships.",
                "evidence": "tests/team_cloud/test_admin_org_api.py",
            },
            {
                "id": "member_lifecycle",
                "summary": "Invite, list, disable, and audit members across owner, admin, member, and guest roles.",
                "evidence": "tests/team_cloud/test_admin_org_api.py",
            },
            {
                "id": "role_permission_matrix",
                "summary": "Use Permission Explorer to verify positive and negative checks before changing access.",
                "evidence": "tests/team_cloud/test_permission_explorer_ga.py",
            },
            {
                "id": "memory_governance",
                "summary": "Review personal and team_shared memory queues, conflicts, PII flags, and retention state.",
                "evidence": "tests/team_cloud/test_memory_review_api.py",
            },
            {
                "id": "backup_restore_operations",
                "summary": "Run personal backup policy, encrypted exports, MinIO upload, restore preview, and restore execute.",
                "evidence": "tests/team_cloud/test_platform_backup_restore_drill.py",
            },
            {
                "id": "tool_policy_management",
                "summary": "Maintain tool risk taxonomy, high-risk approvals, break-glass, and audit trails.",
                "evidence": "tests/team_cloud/test_team_tool_policy_hook.py",
            },
            {
                "id": "audit_review",
                "summary": "Filter audit events by actor, action, decision, resource, and high-risk tool view.",
                "evidence": "tests/team_cloud/test_audit_advanced.py",
            },
        ],
    },
    {
        "id": "user",
        "title": "Team Cloud User Manual",
        "audience": "Team Member",
        "sections": [
            {
                "id": "first_login",
                "summary": "Sign in through Casdoor, confirm membership, and open the web chat entry.",
                "evidence": "tests/team_cloud/test_web_chat_entry.py",
            },
            {
                "id": "team_chat",
                "summary": "Start a team-scoped chat from Web, API, or Gateway identity propagation.",
                "evidence": "tests/team_cloud/test_cloud_session_history.py",
            },
            {
                "id": "personal_memory",
                "summary": "Create, review, archive, restore, and delete personal memory without leaking across members.",
                "evidence": "tests/team_cloud/test_memory_crud_api.py",
            },
            {
                "id": "team_shared_memory",
                "summary": "Use team_shared memory for organization-visible facts with review and dedupe controls.",
                "evidence": "tests/team_cloud/test_memory_prefetch_pipeline.py",
            },
            {
                "id": "review_queue",
                "summary": "Accept, reject, or escalate proposed memory items and conflict candidates.",
                "evidence": "tests/team_cloud/test_memory_review_api.py",
            },
            {
                "id": "backup_self_service",
                "summary": "Understand personal backup cadence, restore preview, and export/delete request flows.",
                "evidence": "tests/team_cloud/test_backup_restore_drill.py",
            },
            {
                "id": "tool_approval_requests",
                "summary": "Request approved high-risk tool use and understand deny reasons from policy decisions.",
                "evidence": "tests/team_cloud/test_team_tool_policy_hook.py",
            },
        ],
    },
)

_WORKFLOWS: tuple[dict[str, Any], ...] = (
    {
        "id": "org_member_management",
        "owner": "Org Owner",
        "steps": ["organization_setup", "member_lifecycle", "role_permission_matrix"],
        "success_criteria": "Disabled members lose relationships and new admins can pass permission checks.",
    },
    {
        "id": "memory_review",
        "owner": "Team Admin",
        "steps": ["memory_governance", "review_queue", "team_shared_memory"],
        "success_criteria": "Accepted team memory is visible only within the organization and personal memory stays isolated.",
    },
    {
        "id": "backup_restore",
        "owner": "SRE or Org Owner",
        "steps": ["backup_restore_operations", "backup_self_service"],
        "success_criteria": "Restore preview is reviewed before execute and audit evidence is retained.",
    },
    {
        "id": "tool_policy_change",
        "owner": "Security Admin",
        "steps": ["tool_policy_management", "tool_approval_requests", "audit_review"],
        "success_criteria": "High-risk tool changes require approval and produce audit events.",
    },
)


def build_admin_user_manual_package() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "name": "team-cloud-admin-user-manuals-v0",
        "manuals": deepcopy(list(_MANUALS)),
        "workflows": deepcopy(list(_WORKFLOWS)),
        "verification": [
            "scripts/run_tests.sh tests/team_cloud/test_admin_user_manuals.py",
            "scripts/team-cloud-foundation-smoke.sh",
        ],
    }


__all__ = ["build_admin_user_manual_package"]
