from __future__ import annotations

import json
import os
from pathlib import Path


SMOKE_MATRIX = Path("teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json")
SMOKE_SCRIPT = Path("scripts/team-cloud-foundation-smoke.sh")


def test_foundation_smoke_matrix_covers_required_platform_domains():
    matrix = json.loads(SMOKE_MATRIX.read_text(encoding="utf-8"))

    domains = {entry["domain"] for entry in matrix["checks"]}

    assert matrix["schema_version"] == 1
    assert {
        "api",
        "auth",
        "authz",
        "authz_chaos",
        "outbox",
        "minio",
        "web",
        "backup_policy",
        "backup_exporter",
        "backup_storage",
        "backup_restore_drill",
        "platform_backup_restore_drill",
        "restore_preview",
        "restore_execute",
        "org_export",
        "deletion_request",
        "hard_delete_worker",
        "retention_policies",
        "break_glass",
        "permission_explorer_ga",
        "audit_advanced",
        "usage_quotas",
        "data_governance_docs",
        "notifications",
        "admin_ux_final",
        "compose_hardening",
        "helm_chart",
        "offline_bundle",
        "security_test_suite",
        "final_security_review",
        "sbom_license_package",
        "install_guide",
        "admin_user_manuals",
        "api_docs",
        "runbook_summary",
        "release_notes",
        "ga_signoff",
        "support_playbook",
        "migration_guide",
        "training_material",
        "final_regression",
        "deployment_smoke",
        "legal_compliance_package",
        "post_ga_backlog",
        "release_manual",
        "ga_release_checklist",
        "upgrade_rollback",
        "performance_tuning",
        "pilot_onboarding",
        "pilot_telemetry_review",
        "bug_triage_process",
        "cost_quota_tuning",
        "chaos_drills",
        "beta_docs",
        "beta_exit_report",
        "i18n_accessibility",
        "metrics_dashboard",
        "logs_traces",
        "load_test_scripts",
    } <= domains
    assert all(entry["command"].startswith("scripts/run_tests.sh ") for entry in matrix["checks"])


def test_foundation_smoke_script_invokes_registered_suite():
    content = SMOKE_SCRIPT.read_text(encoding="utf-8")

    assert os.access(SMOKE_SCRIPT, os.X_OK)
    assert "platform-foundation-smoke-v0.json" in content
    assert "tests/team_cloud/test_casdoor_oidc.py" in content
    assert "tests/team_cloud/test_authz_middleware.py" in content
    assert "tests/team_cloud/test_authz_chaos.py" in content
    assert "tests/team_cloud/test_relationship_outbox.py" in content
    assert "tests/team_cloud/test_minio_manifest.py" in content
    assert "tests/team_cloud/test_web_admin_pages.py" in content
    assert "tests/team_cloud/test_web_chat_entry.py" in content
    assert "tests/team_cloud/test_cloud_session_history.py" in content
    assert "tests/team_cloud/test_sessiondb_import.py" in content
    assert "tests/team_cloud/test_runtime_event_bridge.py" in content
    assert "tests/team_cloud/test_isolation_suite.py" in content
    assert "tests/team_cloud/test_memory_performance_baseline.py" in content
    assert "tests/team_cloud/test_memory_runtime_docs.py" in content
    assert "tests/team_cloud/test_permission_explorer_ga.py" in content
    assert "tests/team_cloud/test_tool_risk_taxonomy.py" in content
    assert "tests/team_cloud/test_team_tool_policy_hook.py" in content
    assert "tests/team_cloud/test_tool_audit.py" in content
    assert "tests/team_cloud/test_backup_policy.py" in content
    assert "tests/team_cloud/test_backup_exporter.py" in content
    assert "tests/team_cloud/test_backup_storage.py" in content
    assert "tests/team_cloud/test_backup_restore_drill.py" in content
    assert "tests/team_cloud/test_platform_backup_restore_drill.py" in content
    assert "tests/team_cloud/test_restore_preview.py" in content
    assert "tests/team_cloud/test_restore_execute.py" in content
    assert "tests/team_cloud/test_org_export.py" in content
    assert "tests/team_cloud/test_deletion_request.py" in content
    assert "tests/team_cloud/test_hard_delete_worker.py" in content
    assert "tests/team_cloud/test_retention_policies.py" in content
    assert "tests/team_cloud/test_break_glass.py" in content
    assert "tests/team_cloud/test_data_governance_docs.py" in content
    assert "tests/team_cloud/test_notifications.py" in content
    assert "tests/team_cloud/test_admin_ux_final.py" in content
    assert "tests/team_cloud/test_compose_hardening.py" in content
    assert "tests/team_cloud/test_helm_chart.py" in content
    assert "tests/team_cloud/test_offline_bundle.py" in content
    assert "tests/team_cloud/test_metrics_dashboard.py" in content
    assert "tests/team_cloud/test_logs_traces.py" in content
    assert "tests/team_cloud/test_load_test_scripts.py" in content
    assert "tests/team_cloud/test_security_test_suite.py" in content
    assert "tests/team_cloud/test_final_security_review.py" in content
    assert "tests/team_cloud/test_sbom_license_package.py" in content
    assert "tests/team_cloud/test_install_guide.py" in content
    assert "tests/team_cloud/test_admin_user_manuals.py" in content
    assert "tests/team_cloud/test_api_docs_package.py" in content
    assert "tests/team_cloud/test_runbook_summary.py" in content
    assert "tests/team_cloud/test_release_notes.py" in content
    assert "tests/team_cloud/test_ga_signoff.py" in content
    assert "tests/team_cloud/test_support_playbook.py" in content
    assert "tests/team_cloud/test_migration_guide.py" in content
    assert "tests/team_cloud/test_training_material.py" in content
    assert "tests/team_cloud/test_final_regression.py" in content
    assert "tests/team_cloud/test_deployment_smoke.py" in content
    assert "tests/team_cloud/test_legal_compliance_package.py" in content
    assert "tests/team_cloud/test_post_ga_backlog.py" in content
    assert "tests/team_cloud/test_release_manual.py" in content
    assert "tests/team_cloud/test_ga_release_checklist.py" in content
    assert "tests/team_cloud/test_upgrade_rollback.py" in content
    assert "tests/team_cloud/test_performance_tuning.py" in content
    assert "tests/team_cloud/test_pilot_onboarding.py" in content
    assert "tests/team_cloud/test_pilot_telemetry_review.py" in content
    assert "tests/team_cloud/test_bug_triage_process.py" in content
    assert "tests/team_cloud/test_cost_quota_tuning.py" in content
    assert "tests/team_cloud/test_chaos_drills.py" in content
    assert "tests/team_cloud/test_beta_docs.py" in content
    assert "tests/team_cloud/test_beta_exit_report.py" in content
    assert "tests/team_cloud/test_i18n_accessibility.py" in content
    assert "tests/team_cloud/test_permission_explorer_minimal.py" in content
    assert "tests/team_cloud/test_audit_advanced.py" in content
    assert "tests/team_cloud/test_usage_quotas.py" in content


def test_admin_disable_outbox_and_permission_explain_share_authz_refs():
    from fastapi.testclient import TestClient

    from team_cloud.admin.organizations import InMemoryOrganizationService
    from team_cloud.api import create_app
    from team_cloud.authz.outbox import InMemoryRelationshipOutboxRepository
    from team_cloud.authz.spicedb import PermissionDecision, ResourceRef, SubjectRef

    outbox = InMemoryRelationshipOutboxRepository()
    service = InMemoryOrganizationService(outbox_repository=outbox)
    admin_client = TestClient(create_app(organization_service=service, oidc_client=object()))
    org = admin_client.post(
        "/api/organizations",
        json={"slug": "hermes-labs", "name": "Hermes Labs"},
    ).json()
    member = admin_client.post(
        f"/api/organizations/{org['id']}/members/invite",
        json={
            "email": "alice@example.com",
            "display_name": "Alice",
            "user_id": "alice",
            "role": "member",
        },
    ).json()

    disabled = admin_client.patch(
        f"/api/organizations/{org['id']}/members/{member['id']}/disable"
    )

    assert disabled.status_code == 200
    assert list(outbox.items.values())[-1].relationships == (
        "organization:hermes-labs#member@user:alice",
    )

    class FakeAuthzClient:
        def check(self, *, subject, resource, action=None, permission=None, consistency=None):
            assert subject == SubjectRef("user", "alice")
            assert resource == ResourceRef("organization", "hermes-labs")
            assert permission == "member"
            return PermissionDecision(
                allowed=False,
                reason="denied",
                subject=subject,
                resource=resource,
                permission="member",
            )

    explain_client = TestClient(
        create_app(authz_client=FakeAuthzClient(), oidc_client=object())
    )
    explained = explain_client.get(
        "/api/authz/explain",
        params={
            "subject_type": "user",
            "subject_id": "alice",
            "resource_type": "organization",
            "resource_id": "hermes-labs",
            "permission": "member",
        },
    )

    assert explained.status_code == 200
    assert explained.json()["cache_key"] == "user:alice|organization:hermes-labs|member"
