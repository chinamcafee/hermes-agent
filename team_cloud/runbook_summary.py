"""Runbook summary package contract for Team Cloud GA."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


_RUNBOOKS: tuple[dict[str, Any], ...] = (
    {
        "id": "backup_restore_failure",
        "owner": "SRE",
        "severity": "P1",
        "signals": ["backup job failed", "restore preview mismatch", "MinIO object missing"],
        "commands": [
            "scripts/team-cloud-backup-restore-drill.py",
            "scripts/run_tests.sh tests/team_cloud/test_platform_backup_restore_drill.py",
        ],
        "verification": ["team-cloud-backup-restore-drill-v0.json status == succeeded"],
        "doc": "teamDoc/GADoc/P4-06-backup-restore-drill.md",
    },
    {
        "id": "casdoor_jwks_rotation_failure",
        "owner": "Backend",
        "severity": "P1",
        "signals": ["JWT verification failure", "OIDC discovery mismatch"],
        "commands": ["scripts/run_tests.sh tests/team_cloud/test_casdoor_oidc.py"],
        "verification": ["OIDC discovery, JWKS, and callback tests pass"],
        "doc": "teamDoc/GADoc/P1-05-casdoor-oidc.md",
    },
    {
        "id": "spicedb_unavailable",
        "owner": "SRE",
        "severity": "P0",
        "signals": ["authorization_unavailable", "SpiceDB gRPC timeout"],
        "commands": [
            "scripts/run_tests.sh tests/team_cloud/test_spicedb_client.py",
            "scripts/run_tests.sh tests/team_cloud/test_authz_middleware.py",
        ],
        "verification": ["AuthZ middleware fails closed and denies protected routes"],
        "doc": "teamDoc/GADoc/P1-12-authz-middleware.md",
    },
    {
        "id": "postgres_slow_pgvector_query",
        "owner": "Database",
        "severity": "P2",
        "signals": ["memory prefetch p95 exceeds 500 ms", "pgvector index scan missing"],
        "commands": [
            "scripts/team-cloud-memory-perf-baseline.py",
            "scripts/run_tests.sh tests/team_cloud/test_memory_performance_baseline.py",
        ],
        "verification": ["memory-performance-baseline-v0.json p95 targets stay within threshold"],
        "doc": "teamDoc/GADoc/P2-21-memory-performance-baseline.md",
    },
    {
        "id": "minio_upload_failure",
        "owner": "SRE",
        "severity": "P1",
        "signals": ["manifest write failed", "signed URL unavailable", "bucket policy mismatch"],
        "commands": [
            "scripts/run_tests.sh tests/team_cloud/test_minio_manifest.py",
            "scripts/run_tests.sh tests/team_cloud/test_backup_storage.py",
        ],
        "verification": ["MinIO manifest and backup storage tests pass"],
        "doc": "teamDoc/GADoc/P1-15-minio-manifest.md",
    },
    {
        "id": "outbox_dead_letter",
        "owner": "Backend",
        "severity": "P1",
        "signals": ["relationship outbox retries exhausted", "authz pending relationship sync"],
        "commands": ["scripts/run_tests.sh tests/team_cloud/test_relationship_outbox.py"],
        "verification": ["outbox retries, dead-letter state, and audit events are present"],
        "doc": "teamDoc/GADoc/P1-11-relationship-outbox.md",
    },
    {
        "id": "upgrade_rollback",
        "owner": "Release",
        "severity": "P1",
        "signals": ["post-upgrade smoke failed", "migration checksum mismatch"],
        "commands": ["scripts/team-cloud-upgrade-rollback-plan.py"],
        "verification": [
            "scripts/team-cloud-foundation-smoke.sh",
            "team-cloud-upgrade-rollback-v0.json migration checksums match",
        ],
        "doc": "teamDoc/GADoc/P4-09-upgrade-rollback.md",
    },
    {
        "id": "cross_tenant_access_alert",
        "owner": "Security",
        "severity": "P0",
        "signals": ["cross-tenant access alert", "unexpected personal memory hit"],
        "commands": [
            "scripts/team-cloud-isolation-smoke.sh",
            "scripts/run_tests.sh tests/team_cloud/test_isolation_suite.py",
            "scripts/run_tests.sh tests/team_cloud/test_authz_chaos.py",
        ],
        "verification": ["cross-tenant access success count remains 0"],
        "doc": "teamDoc/GADoc/P2-20-isolation-suite.md",
    },
    {
        "id": "destructive_tool_abuse_alert",
        "owner": "Security",
        "severity": "P0",
        "signals": ["break-glass abuse", "high-risk tool bypass attempt"],
        "commands": [
            "scripts/run_tests.sh tests/team_cloud/test_team_tool_policy_hook.py",
            "scripts/run_tests.sh tests/team_cloud/test_break_glass.py",
        ],
        "verification": ["high-risk tool bypass count remains 0"],
        "doc": "teamDoc/GADoc/P3-14-break-glass.md",
    },
)

_DRILL_EVIDENCE: tuple[dict[str, str], ...] = (
    {
        "id": "backup_restore_drill",
        "artifact": "teamDoc/GADoc/artifacts/drills/team-cloud-backup-restore-drill-v0.json",
    },
    {
        "id": "authz_chaos",
        "artifact": "teamDoc/GADoc/artifacts/chaos/team-cloud-chaos-drills-v0.json",
    },
    {
        "id": "upgrade_rollback",
        "artifact": "teamDoc/GADoc/artifacts/release/team-cloud-upgrade-rollback-v0.json",
    },
)


def build_runbook_summary_package() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "name": "team-cloud-runbook-summary-v0",
        "runbooks": deepcopy(list(_RUNBOOKS)),
        "drill_evidence": deepcopy(list(_DRILL_EVIDENCE)),
        "escalation": {
            "p0_p1_security_defects_allowed": 0,
            "p0_response_minutes": 15,
            "p1_response_minutes": 60,
            "required_channels": ["security", "sre", "release"],
        },
        "verification": [
            "scripts/run_tests.sh tests/team_cloud/test_runbook_summary.py",
            "scripts/team-cloud-foundation-smoke.sh",
        ],
    }


__all__ = ["build_runbook_summary_package"]
