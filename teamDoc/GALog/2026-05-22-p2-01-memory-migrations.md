# P2-01 记忆迁移表工作日志

## 目标

- 按 `GAStep` 顺序推进 P2-01。
- 在 P0/P1 基础 schema 上追加 P2 memory runtime migration。
- 确保 migration runner 和 compose 迁移作业按顺序应用所有 SQL migration。

## 执行记录

- 2026-05-22：启动 P2-01，读取 P2 memory runtime steps、P0 PostgreSQL schema、P1 migration runner 和 compose 迁移作业。
- 2026-05-22：按 TDD 新增 `tests/team_cloud/test_memory_migrations.py`，并扩展 `tests/team_cloud/test_postgres_migrations.py`，覆盖 `002_memory_runtime_schema.sql`、rollback note、runner 顺序和 compose 全量 SQL 应用。
- 2026-05-22：红灯确认后新增 `002_memory_runtime_schema.sql`、rollback note，并更新 `team-migrate` 挂载目录和循环应用逻辑。
- 2026-05-22：更新 smoke matrix 和 `scripts/team-cloud-foundation-smoke.sh`，纳入 memory migration 测试。
- 2026-05-22：新增 `teamDoc/GADoc/P2-01-memory-migrations.md`。

## 验证记录

- 红灯：`scripts/run_tests.sh tests/team_cloud/test_memory_migrations.py tests/team_cloud/test_postgres_migrations.py`
  - 结果：`5 tests failed, 4 passed`。
  - 失败点：缺少 `002_memory_runtime_schema.sql` 和 rollback note；migration runner 只发现 001；compose `team-migrate` 只挂载并应用单个 `001_schema_v0.sql`。
- 绿灯：`scripts/run_tests.sh tests/team_cloud/test_memory_migrations.py tests/team_cloud/test_postgres_migrations.py`
  - 结果：`9 tests passed, 0 failed`。
- Smoke 回归：`scripts/team-cloud-foundation-smoke.sh`
  - 结果：`100 tests passed, 0 failed`。
- Ruff 回归：`venv/bin/ruff check team_cloud tests/team_cloud`
  - 结果：`All checks passed!`。
- 语法检查：`venv/bin/python -m compileall -q team_cloud`
  - 结果：退出码 0。
