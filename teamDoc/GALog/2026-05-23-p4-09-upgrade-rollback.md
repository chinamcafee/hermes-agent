# P4-09 Upgrade/rollback 工作日志

## 背景

- 工作包：`P4-09 | Upgrade/rollback | migrations、image rollback、schema compatibility | P4-02 | 2.5`
- 当前阶段：P4 Beta 验证，P4-01 到 P4-08 已完成。
- 设计依据：
  - P1/P2 已提供 SQL migrations 和 rollback notes。
  - P4-02/P4-03 已提供 Helm chart 和 offline bundle。
  - P4-09 需要把升级、回滚、schema 兼容和 smoke 验证顺序固化。

## 执行计划

1. 用 contract 测试定义 upgrade/rollback plan、artifact、脚本和 smoke 注册。
2. 新增 plan builder 和生成脚本，包含 migration checksum、Helm/compose/offline 回滚动作。
3. 新增 P4-09 文档和 JSON artifact。
4. 运行红灯、绿灯、回归、静态检查和完整 smoke。

## 实时记录

- 2026-05-23：P4-09 已在进度表中标记为 In Progress，开始按 TDD 红绿循环推进。
- 2026-05-23：红灯验证已执行，`scripts/run_tests.sh tests/team_cloud/test_upgrade_rollback.py` 出现 2 个预期失败，指向 `team_cloud.upgrade` 缺失和 upgrade/rollback artifact/docs/smoke 注册缺口。
- 2026-05-23：新增 `team_cloud/upgrade.py`、`scripts/team-cloud-upgrade-rollback-plan.py`、P4-09 文档和 upgrade/rollback artifact，覆盖 migrations、SpiceDB schema compatibility、Helm/Compose deploy、offline upgrade、post-upgrade smoke、image rollback 和数据库恢复回滚。
- 2026-05-23：升级/回滚计划生成脚本通过，`scripts/team-cloud-upgrade-rollback-plan.py --output teamDoc/GADoc/artifacts/release/team-cloud-upgrade-rollback-v0.json` 输出 `status=written`。
- 2026-05-23：绿灯验证通过，`scripts/run_tests.sh tests/team_cloud/test_upgrade_rollback.py` 结果为 1 个文件、2 个测试通过。
- 2026-05-23：相关回归通过，`scripts/run_tests.sh tests/team_cloud/test_upgrade_rollback.py tests/team_cloud/test_postgres_migrations.py tests/team_cloud/test_helm_chart.py tests/team_cloud/test_offline_bundle.py tests/team_cloud/test_platform_foundation_suite.py` 结果为 5 个文件、18 个测试通过。
- 2026-05-23：静态验证通过，`venv/bin/ruff check ...`、`venv/bin/python -m py_compile ...`、`venv/bin/python -m json.tool teamDoc/GADoc/artifacts/release/team-cloud-upgrade-rollback-v0.json >/dev/null`、`venv/bin/python -m json.tool teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json >/dev/null` 和 `git diff --check ...` 均为 exit 0。
- 2026-05-23：完整 foundation smoke 通过，`scripts/team-cloud-foundation-smoke.sh` 结果为 77 个文件、263 个测试通过。
