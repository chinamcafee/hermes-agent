# P4-09 Upgrade/rollback

日期：2026-05-23
状态：Implemented
前置：`P4-02 Helm chart`

## 目标

本步骤固定 Team Cloud Beta 升级/回滚 contract，覆盖 SQL migrations、SpiceDB schema compatibility、Helm/Compose image rollback、offline bundle upgrade、post-upgrade smoke 和数据库恢复回滚。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/upgrade.py` | `build_upgrade_rollback_plan()` 生成升级/回滚计划。 |
| `scripts/team-cloud-upgrade-rollback-plan.py` | 写出 upgrade/rollback JSON artifact。 |
| `teamDoc/GADoc/artifacts/release/team-cloud-upgrade-rollback-v0.json` | P4-09 升级/回滚计划 artifact。 |
| `tests/team_cloud/test_upgrade_rollback.py` | P4-09 contract 测试。 |

## 步骤

| Step | 目的 |
| --- | --- |
| `preflight_backup` | 升级前确认 P4-06 备份恢复演练通过。 |
| `database_migrations` | 应用 SQL migrations 并固定 checksum。 |
| `spicedb_schema_compatibility` | 验证 SpiceDB schema 和权限 fixture。 |
| `helm_or_compose_deploy` | Helm/Compose 部署新版本。 |
| `offline_bundle_upgrade` | 离线包升级和 checksum 校验。 |
| `post_upgrade_smoke` | 升级后运行 foundation smoke。 |
| `image_rollback` | 失败时回滚 Helm release / image digest。 |
| `database_restore_rollback` | 失败时恢复 PostgreSQL PITR 和 SpiceDB snapshot。 |

## 运行

```bash
scripts/team-cloud-upgrade-rollback-plan.py --output teamDoc/GADoc/artifacts/release/team-cloud-upgrade-rollback-v0.json
```

## 验证

```bash
scripts/run_tests.sh tests/team_cloud/test_upgrade_rollback.py
scripts/run_tests.sh tests/team_cloud/test_upgrade_rollback.py tests/team_cloud/test_postgres_migrations.py tests/team_cloud/test_helm_chart.py tests/team_cloud/test_offline_bundle.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/ruff check team_cloud/upgrade.py scripts/team-cloud-upgrade-rollback-plan.py tests/team_cloud/test_upgrade_rollback.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m py_compile team_cloud/upgrade.py scripts/team-cloud-upgrade-rollback-plan.py tests/team_cloud/test_upgrade_rollback.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m json.tool teamDoc/GADoc/artifacts/release/team-cloud-upgrade-rollback-v0.json >/dev/null
scripts/team-cloud-foundation-smoke.sh
```
