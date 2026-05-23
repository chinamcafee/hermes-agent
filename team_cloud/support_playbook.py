"""Support playbook package contract for Team Cloud GA."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


_SUPPORT_TIERS: tuple[dict[str, Any], ...] = (
    {"severity": "P0", "first_response_minutes": 15, "target_update_minutes": 30},
    {"severity": "P1", "first_response_minutes": 60, "target_update_minutes": 120},
    {"severity": "P2", "first_response_minutes": 240, "target_update_minutes": 480},
    {"severity": "P3", "first_response_minutes": 1440, "target_update_minutes": 2880},
)

_DIAGNOSTIC_COMMANDS: tuple[dict[str, str], ...] = (
    {
        "id": "foundation_smoke",
        "command": "scripts/team-cloud-foundation-smoke.sh",
        "purpose": "Confirm Team Cloud GA contract still passes.",
    },
    {
        "id": "collect_hermes_logs",
        "command": "hermes logs --level WARNING --session <session-id>",
        "purpose": "Collect agent.log, errors.log, and gateway.log slices.",
    },
    {
        "id": "runbook_summary",
        "command": "scripts/team-cloud-runbook-summary.py",
        "purpose": "Refresh runbook artifact and select incident-specific runbook.",
    },
    {
        "id": "audit_export",
        "command": "GET /api/audit/export?org_id=<org-id>",
        "purpose": "Export audit evidence for the support case.",
    },
)

_LOG_COLLECTION: tuple[dict[str, str], ...] = (
    {"id": "agent_log", "source": "~/.hermes/logs/agent.log"},
    {"id": "errors_log", "source": "~/.hermes/logs/errors.log"},
    {"id": "gateway_log", "source": "~/.hermes/logs/gateway.log"},
    {"id": "team_api_logs", "source": "team-api container or pod logs"},
    {"id": "audit_export", "source": "/api/audit/export"},
)

_ESCALATION_PATHS: tuple[dict[str, str], ...] = (
    {"id": "security", "trigger": "P0/P1 security, cross-tenant, or tool abuse"},
    {"id": "sre", "trigger": "availability, backup, restore, MinIO, PostgreSQL, or SpiceDB"},
    {"id": "release", "trigger": "upgrade, rollback, migration, or release artifact issue"},
)


def build_support_playbook_package() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "name": "team-cloud-support-playbook-v0",
        "support_tiers": deepcopy(list(_SUPPORT_TIERS)),
        "diagnostic_commands": deepcopy(list(_DIAGNOSTIC_COMMANDS)),
        "log_collection": deepcopy(list(_LOG_COLLECTION)),
        "escalation_paths": deepcopy(list(_ESCALATION_PATHS)),
        "upgrade_path": "P5-06 runbook_summary -> P4-09 upgrade_rollback",
        "handoff_artifacts": [
            "support_case_template",
            "customer_export_bundle",
            "audit_jsonl_export",
        ],
        "verification": [
            "scripts/run_tests.sh tests/team_cloud/test_support_playbook.py",
            "scripts/team-cloud-foundation-smoke.sh",
        ],
    }


__all__ = ["build_support_playbook_package"]
