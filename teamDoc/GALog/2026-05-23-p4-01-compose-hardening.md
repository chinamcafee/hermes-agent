# P4-01 Compose hardening 工作日志

## 背景

- 工作包：`P4-01 | Compose hardening | healthcheck、volumes、TLS/dev cert、backup mount | P3 | 1.5`
- 当前阶段：P4 Beta 验证，P0-P3/M0-M3 已关闭。
- 设计依据：
  - `teamDoc/GAStep/05-phase-4-5-beta-ga-steps.md` 的部署硬化要求。
  - `deploy/team-cloud/compose.yaml` 已有本地基础拓扑和核心服务。

## 执行计划

1. 用静态 compose contract 测试定义 P4-01 硬化边界。
2. 补齐长期服务 healthcheck、固定 backup mount 和 dev TLS mount。
3. 更新 `.env.example`、部署文档和 foundation smoke 覆盖。
4. 运行 P4-01 单测、compose 回归、JSON/ruff/py_compile/diff 检查和 foundation smoke。

## 实时记录

- 2026-05-23：P4-01 标记为 In Progress，开始按 TDD 红绿循环推进。
- 2026-05-23：红灯验证已执行，`scripts/run_tests.sh tests/team_cloud/test_compose_hardening.py` 出现 3 个预期失败，分别指向长期服务 healthcheck、backup/dev TLS mount、文档和 smoke 注册缺口。
- 2026-05-23：补齐 `deploy/team-cloud/compose.yaml` 的 P4-01 hardening contract，新增 `backups` 与 `certs/dev` 保留目录，更新 `.env.example`、`.gitignore`、smoke 矩阵和 P4-01 文档。
- 2026-05-23：绿灯验证通过，`scripts/run_tests.sh tests/team_cloud/test_compose_hardening.py` 结果为 1 个文件、3 个测试通过。
- 2026-05-23：相关回归通过，`scripts/run_tests.sh tests/team_cloud/test_compose_hardening.py tests/team_cloud/test_local_compose_stack.py tests/team_cloud/test_platform_foundation_suite.py` 结果为 3 个文件、13 个测试通过。
- 2026-05-23：静态验证通过，`venv/bin/ruff check ...`、`venv/bin/python -m py_compile ...`、`venv/bin/python -m json.tool teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json >/dev/null`、`docker compose -f deploy/team-cloud/compose.yaml --env-file deploy/team-cloud/.env.example config >/dev/null` 和 `git diff --check ...` 均为 exit 0。
- 2026-05-23：完整 foundation smoke 通过，`scripts/team-cloud-foundation-smoke.sh` 结果为 69 个文件、243 个测试通过。
