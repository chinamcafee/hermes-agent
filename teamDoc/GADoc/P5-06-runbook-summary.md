# P5-06 Runbook 汇总

日期：2026-05-23
状态：Implemented
前置：`P4-06 备份恢复演练`、`P4-09 Upgrade/rollback`、`P5-05 API 文档`

## 目标

本步骤固定 Team Cloud GA Runbook 汇总 contract，把 backup/restore、outage、upgrade、rollback 和安全告警处置路径集中到一个 release artifact。该汇总不替代原始 Runbook，而是给 on-call、SRE、Security 和 Release owner 一个入口索引。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/runbook_summary.py` | `build_runbook_summary_package()` 生成 Runbook 汇总 JSON contract。 |
| `scripts/team-cloud-runbook-summary.py` | 写出 Runbook 汇总 JSON artifact。 |
| `teamDoc/GADoc/artifacts/release/team-cloud-runbook-summary-v0.json` | P5-06 Runbook 汇总 artifact。 |
| `tests/team_cloud/test_runbook_summary.py` | P5-06 contract 测试。 |

## Runbook 索引

| Runbook | Owner | Severity | 主要信号 | 处置入口 |
| --- | --- | --- | --- | --- |
| `backup_restore_failure` | SRE | P1 | backup job failed、restore preview mismatch、MinIO object missing | `scripts/team-cloud-backup-restore-drill.py` |
| `casdoor_jwks_rotation_failure` | Backend | P1 | JWT verification failure、OIDC discovery mismatch | `tests/team_cloud/test_casdoor_oidc.py` |
| `spicedb_unavailable` | SRE | P0 | `authorization_unavailable`、SpiceDB gRPC timeout | `tests/team_cloud/test_spicedb_client.py`、`tests/team_cloud/test_authz_middleware.py` |
| `postgres_slow_pgvector_query` | Database | P2 | memory prefetch P95 超过 500 ms、pgvector index scan 缺失 | `scripts/team-cloud-memory-perf-baseline.py` |
| `minio_upload_failure` | SRE | P1 | manifest write failed、signed URL unavailable、bucket policy mismatch | `tests/team_cloud/test_minio_manifest.py`、`tests/team_cloud/test_backup_storage.py` |
| `outbox_dead_letter` | Backend | P1 | relationship outbox retries exhausted、authz pending relationship sync | `tests/team_cloud/test_relationship_outbox.py` |
| `upgrade_rollback` | Release | P1 | post-upgrade smoke failed、migration checksum mismatch | `scripts/team-cloud-upgrade-rollback-plan.py`、`scripts/team-cloud-foundation-smoke.sh` |
| `cross_tenant_access_alert` | Security | P0 | cross-tenant access alert、unexpected personal memory hit | `scripts/team-cloud-isolation-smoke.sh`、`tests/team_cloud/test_authz_chaos.py` |
| `destructive_tool_abuse_alert` | Security | P0 | break-glass abuse、高危工具绕过尝试 | `tests/team_cloud/test_team_tool_policy_hook.py`、`tests/team_cloud/test_break_glass.py` |

## 演练证据

| Drill | Artifact |
| --- | --- |
| `backup_restore_drill` | `teamDoc/GADoc/artifacts/drills/team-cloud-backup-restore-drill-v0.json` |
| `authz_chaos` | `teamDoc/GADoc/artifacts/chaos/team-cloud-chaos-drills-v0.json` |
| `upgrade_rollback` | `teamDoc/GADoc/artifacts/release/team-cloud-upgrade-rollback-v0.json` |

## 升级和回滚

`upgrade_rollback` Runbook 必须在维护窗口内先运行备份演练，再执行 migration/schema/chart/offline bundle 步骤。失败时按 P4-09 的 image rollback 和 database restore rollback 执行，并以 `scripts/team-cloud-foundation-smoke.sh` 作为恢复验证。

## Escalation

- P0/P1 安全缺陷允许数：`0`。
- P0 首响：15 分钟。
- P1 首响：60 分钟。
- 必须通知：security、sre、release。

## 运行

```bash
scripts/team-cloud-runbook-summary.py --output teamDoc/GADoc/artifacts/release/team-cloud-runbook-summary-v0.json
```

## 验证

```bash
scripts/run_tests.sh tests/team_cloud/test_runbook_summary.py
scripts/run_tests.sh tests/team_cloud/test_runbook_summary.py tests/team_cloud/test_platform_backup_restore_drill.py tests/team_cloud/test_authz_chaos.py tests/team_cloud/test_upgrade_rollback.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/ruff check team_cloud/runbook_summary.py scripts/team-cloud-runbook-summary.py tests/team_cloud/test_runbook_summary.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m py_compile team_cloud/runbook_summary.py scripts/team-cloud-runbook-summary.py tests/team_cloud/test_runbook_summary.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m json.tool teamDoc/GADoc/artifacts/release/team-cloud-runbook-summary-v0.json >/dev/null
scripts/team-cloud-foundation-smoke.sh
```
