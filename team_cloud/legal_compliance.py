"""Legal and compliance package contract for Team Cloud GA."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


_EVIDENCE: tuple[dict[str, Any], ...] = (
    {
        "id": "sbom_license",
        "artifact": "teamDoc/GADoc/artifacts/release/team-cloud-sbom-license-v0.json",
        "documents": ["P5-02-sbom-license-package.md"],
        "controls": ["sbom", "license_report", "risk_closures"],
    },
    {
        "id": "minio_agpl_notice",
        "artifact": "teamDoc/GADoc/artifacts/release/team-cloud-sbom-license-v0.json",
        "license": "AGPL-3.0",
        "obligations": [
            "source_offer_required",
            "network_service_source_availability_reviewed",
            "customer_notice_required",
        ],
    },
    {
        "id": "final_security_review",
        "artifact": "teamDoc/GADoc/artifacts/security/team-cloud-final-security-review-v0.json",
        "documents": ["P5-01-final-security-review.md"],
        "controls": ["authn_authz", "memory_isolation", "tool_policy", "audit_redaction"],
    },
    {
        "id": "data_governance",
        "documents": ["P3-20-data-governance-runbooks.md"],
        "controls": ["export", "deletion", "retention", "break_glass", "audit"],
    },
    {
        "id": "privacy_export_delete_retention",
        "documents": [
            "P3-10-org-export.md",
            "P3-11-deletion-request.md",
            "P3-13-retention-policies.md",
        ],
        "controls": ["org_export", "deletion_request", "retention_policies"],
    },
)


def build_legal_compliance_package() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "name": "team-cloud-legal-compliance-v0",
        "evidence": deepcopy(list(_EVIDENCE)),
        "review_signoffs": [
            "legal_review",
            "security_review",
            "data_protection_review",
            "release_owner_review",
        ],
        "acceptance_thresholds": {
            "unknown_licenses": 0,
            "missing_license_notices": 0,
            "open_critical_or_high_security_findings": 0,
            "uncovered_privacy_controls": 0,
        },
        "exit_decision": "required_for_ga",
        "verification": [
            "scripts/run_tests.sh tests/team_cloud/test_legal_compliance_package.py",
            "scripts/team-cloud-foundation-smoke.sh",
        ],
    }


__all__ = ["build_legal_compliance_package"]
