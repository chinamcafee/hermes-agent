"""Post-GA backlog package contract for Team Cloud GA."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


_ITEMS: tuple[dict[str, Any], ...] = (
    {
        "id": "helm_runtime_lint_ci",
        "category": "release_engineering",
        "priority": "P1",
        "owner": "SRE",
        "ga_blocker": False,
        "rationale": "Move helm lint from local gap note to CI runtime validation.",
    },
    {
        "id": "advanced_admin_analytics",
        "category": "product",
        "priority": "P2",
        "owner": "Product + Frontend",
        "ga_blocker": False,
        "rationale": "Add richer admin usage and policy analytics after GA telemetry stabilizes.",
    },
    {
        "id": "memory_quality_iteration",
        "category": "memory_runtime",
        "priority": "P1",
        "owner": "Runtime",
        "ga_blocker": False,
        "rationale": "Tune extraction quality using production feedback without changing GA contracts.",
    },
    {
        "id": "external_audit_packet",
        "category": "compliance",
        "priority": "P2",
        "owner": "Security + Legal",
        "ga_blocker": False,
        "rationale": "Prepare customer-facing audit packet from P5 legal/compliance evidence.",
    },
)


def build_post_ga_backlog_package() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "name": "team-cloud-post-ga-backlog-v0",
        "items": deepcopy(list(_ITEMS)),
        "acceptance_thresholds": {
            "ga_blocking_items": 0,
            "items_without_owner": 0,
            "items_without_priority": 0,
        },
        "exit_decision": "non_blocking_post_ga",
        "m5_closure": {
            "status": "signed",
            "depends_on": [
                "P5-12-final-regression",
                "P5-13-deployment-smoke",
                "P5-14-legal-compliance-package",
            ],
        },
        "verification": [
            "scripts/run_tests.sh tests/team_cloud/test_post_ga_backlog.py",
            "scripts/team-cloud-foundation-smoke.sh",
        ],
    }


__all__ = ["build_post_ga_backlog_package"]
