# P4-13 Chaos drills 工作日志

## 背景

- 工作包：`P4-13 | Chaos drills | SpiceDB/MinIO/PostgreSQL partial failure | P4-06 | 2`
- 当前阶段：P4 Beta 验证，P4-01 到 P4-12 已完成。

## 执行计划

1. 用 contract 测试定义 chaos drill 矩阵、artifact、脚本和 smoke 注册。
2. 新增 chaos builder 和生成脚本。
3. 新增 P4-13 文档和 JSON artifact。
4. 运行红灯、绿灯、回归、静态检查和完整 smoke。

## 实时记录

- 2026-05-23：P4-13 已在进度表中标记为 In Progress，开始按 TDD 红绿循环推进。
- 2026-05-23：红灯验证已执行，`scripts/run_tests.sh tests/team_cloud/test_chaos_drills.py` 出现 2 个预期失败，指向 `team_cloud.chaos` 缺失和 chaos artifact/docs/smoke 注册缺口。
- 2026-05-23：新增 `team_cloud/chaos.py`、`scripts/team-cloud-chaos-drills.py`、`tests/team_cloud/test_chaos_drills.py`、`teamDoc/GADoc/P4-13-chaos-drills.md` 和 `teamDoc/GADoc/artifacts/chaos/team-cloud-chaos-drills-v0.json`，覆盖 SpiceDB、MinIO、PostgreSQL、Casdoor、worker、gateway partial failure 的演练矩阵。
- 2026-05-23：已把 P4-13 纳入 `scripts/team-cloud-foundation-smoke.sh`、`tests/team_cloud/test_platform_foundation_suite.py` 和 `teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json`。
- 2026-05-23：生成脚本验证通过，`scripts/team-cloud-chaos-drills.py --output teamDoc/GADoc/artifacts/chaos/team-cloud-chaos-drills-v0.json` 输出 `status=written`。
- 2026-05-23：回归验证通过，`scripts/run_tests.sh tests/team_cloud/test_chaos_drills.py tests/team_cloud/test_authz_chaos.py tests/team_cloud/test_backup_storage.py tests/team_cloud/test_notifications.py tests/team_cloud/test_platform_foundation_suite.py` 通过 5 个文件 / 17 个测试。
- 2026-05-23：静态验证通过，`venv/bin/ruff check team_cloud/chaos.py scripts/team-cloud-chaos-drills.py tests/team_cloud/test_chaos_drills.py tests/team_cloud/test_platform_foundation_suite.py`、`venv/bin/python -m py_compile ...`、JSON artifact 检查和 `git diff --check` 均为 exit 0。
- 2026-05-23：完整 foundation smoke 通过，`scripts/team-cloud-foundation-smoke.sh` 覆盖 81 个文件 / 271 个测试。
