"""GA release notes package contract for Team Cloud."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


_BREAKING_CHANGES: tuple[dict[str, str], ...] = (
    {
        "id": "casdoor_identity_required",
        "summary": "Team Cloud requires Casdoor-backed identity for web and API access.",
    },
    {
        "id": "team_scoped_memory",
        "summary": "Memory is separated into personal and team_shared scopes with org/team context.",
    },
    {
        "id": "tool_policy_enforced",
        "summary": "High-risk tools are gated by TeamToolPolicyHook and audit requirements.",
    },
)

_UPGRADE_NOTES: tuple[dict[str, str], ...] = (
    {"id": "compose", "summary": "Use deploy/team-cloud/compose.yaml for local GA install."},
    {
        "id": "helm",
        "summary": "Use deploy/team-cloud/helm/hermes-team-cloud/Chart.yaml for Kubernetes.",
    },
    {
        "id": "offline_bundle",
        "summary": "Ship offline manifest, images, and checksums for restricted-network installs.",
    },
    {
        "id": "migration_checksums",
        "summary": "Verify SQL migration checksums before and after upgrade/rollback.",
    },
)

_KNOWN_ISSUES: tuple[dict[str, Any], ...] = (
    {
        "id": "helm_lint_not_run_locally",
        "severity": "P3",
        "ga_blocking": False,
        "summary": "Local environment may not include helm; chart contract is covered by static tests.",
    },
    {
        "id": "external_sso_variants_post_ga",
        "severity": "P3",
        "ga_blocking": False,
        "summary": "Only Casdoor-backed default SSO path is GA; additional IdP variants remain Post-GA.",
    },
)

_EVIDENCE_LINKS: tuple[dict[str, str], ...] = (
    {
        "id": "final_security_review",
        "path": "teamDoc/GADoc/artifacts/security/team-cloud-final-security-review-v0.json",
    },
    {
        "id": "sbom_license",
        "path": "teamDoc/GADoc/artifacts/release/team-cloud-sbom-license-v0.json",
    },
    {
        "id": "install_guide",
        "path": "teamDoc/GADoc/artifacts/release/team-cloud-install-guide-v0.json",
    },
    {
        "id": "runbook_summary",
        "path": "teamDoc/GADoc/artifacts/release/team-cloud-runbook-summary-v0.json",
    },
)


def build_release_notes_package() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "name": "team-cloud-ga-release-notes-v0",
        "release_channel": "GA",
        "release_status": "ga_ready",
        "release_date": "2026-05-23",
        "highlights": [
            "enterprise_team_cloud",
            "two_tier_memory",
            "local_memory_backup",
            "casdoor_spicedb_postgres_minio_stack",
            "tool_policy_and_audit",
        ],
        "breaking_changes": deepcopy(list(_BREAKING_CHANGES)),
        "upgrade_notes": deepcopy(list(_UPGRADE_NOTES)),
        "known_issues": deepcopy(list(_KNOWN_ISSUES)),
        "evidence_links": deepcopy(list(_EVIDENCE_LINKS)),
        "verification": [
            "scripts/run_tests.sh tests/team_cloud/test_release_notes.py",
            "scripts/team-cloud-foundation-smoke.sh",
        ],
    }


__all__ = ["build_release_notes_package"]
