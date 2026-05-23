"""GA sign-off register package contract for Team Cloud."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


_SIGNOFFS: tuple[dict[str, str], ...] = (
    {
        "domain": "product_requirements",
        "owner": "Product",
        "status": "signed_for_ga",
        "evidence": "teamDoc/GADoc/P0-10-ga-acceptance-matrix.md",
    },
    {
        "domain": "authn_authz",
        "owner": "Backend + Security",
        "status": "signed_for_ga",
        "evidence": "teamDoc/GADoc/artifacts/security/team-cloud-final-security-review-v0.json",
    },
    {
        "domain": "memory_isolation",
        "owner": "Runtime + QA",
        "status": "signed_for_ga",
        "evidence": "teamDoc/GADoc/artifacts/p2-isolation-suite-v0.json",
    },
    {
        "domain": "backup_restore",
        "owner": "SRE",
        "status": "signed_for_ga",
        "evidence": "teamDoc/GADoc/artifacts/drills/team-cloud-backup-restore-drill-v0.json",
    },
    {
        "domain": "web_console",
        "owner": "Frontend",
        "status": "signed_for_ga",
        "evidence": "teamDoc/GADoc/P3-22-admin-ux-final.md",
    },
    {
        "domain": "documentation",
        "owner": "Product + Engineering",
        "status": "signed_for_ga",
        "evidence": "teamDoc/GADoc/P5-04-admin-user-manuals.md",
    },
    {
        "domain": "security_review",
        "owner": "Security",
        "status": "signed_for_ga",
        "evidence": "teamDoc/GADoc/P5-01-final-security-review.md",
    },
    {
        "domain": "pilot_acceptance",
        "owner": "Customer/Internal",
        "status": "signed_for_ga",
        "evidence": "teamDoc/GADoc/artifacts/pilot/team-cloud-beta-exit-report-v0.json",
    },
    {
        "domain": "release_operations",
        "owner": "Release",
        "status": "signed_for_ga",
        "evidence": "teamDoc/GADoc/P5-06-runbook-summary.md",
    },
)

_EVIDENCE_LINKS: tuple[dict[str, str], ...] = (
    {
        "id": "final_security_review",
        "path": "teamDoc/GADoc/artifacts/security/team-cloud-final-security-review-v0.json",
    },
    {
        "id": "beta_exit_report",
        "path": "teamDoc/GADoc/artifacts/pilot/team-cloud-beta-exit-report-v0.json",
    },
    {
        "id": "release_notes",
        "path": "teamDoc/GADoc/artifacts/release/team-cloud-ga-release-notes-v0.json",
    },
    {
        "id": "runbook_summary",
        "path": "teamDoc/GADoc/artifacts/release/team-cloud-runbook-summary-v0.json",
    },
    {
        "id": "final_regression",
        "path": "teamDoc/GADoc/artifacts/release/team-cloud-final-regression-v0.json",
    },
    {
        "id": "deployment_smoke",
        "path": "teamDoc/GADoc/artifacts/release/team-cloud-deployment-smoke-v0.json",
    },
    {
        "id": "legal_compliance",
        "path": "teamDoc/GADoc/artifacts/release/team-cloud-legal-compliance-v0.json",
    },
    {
        "id": "post_ga_backlog",
        "path": "teamDoc/GADoc/artifacts/release/team-cloud-post-ga-backlog-v0.json",
    },
)


def build_ga_signoff_package() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "name": "team-cloud-ga-sign-off-v0",
        "gate": "ga",
        "m5_final_signoff": "signed",
        "blocking_issues": {"p0_open": 0, "p1_open": 0},
        "signoffs": deepcopy(list(_SIGNOFFS)),
        "evidence_links": deepcopy(list(_EVIDENCE_LINKS)),
        "verification": [
            "scripts/run_tests.sh tests/team_cloud/test_ga_signoff.py",
            "scripts/team-cloud-foundation-smoke.sh",
        ],
    }


__all__ = ["build_ga_signoff_package"]
