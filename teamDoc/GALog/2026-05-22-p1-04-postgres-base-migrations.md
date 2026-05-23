# P1-04 PostgreSQL 基础迁移

## 工作目标

- 按 `teamDoc/GAStep/01-work-package-register.md` 的 P1-04 执行。
- 主要产出：org/user/member/team/project/audit/outbox 基表迁移。
- 将 P0-08 `001_schema_v0.sql` 提升为 Team Cloud package 内的可执行迁移工件。
- 为 migration runner 增加 checksum、rollback note 和 psql apply 命令。
- 将 P1-03 compose 中的 Team API 启动顺序改为依赖 `team-migrate`。

## 2026-05-22 执行记录

### 1. 启动 P1-04

- 前置确认：P1-01 到 P1-03 已在 `progress-tracker.md` 标记 `Done`。
- 规格输入：`teamDoc/GADoc/P0-08-postgres-pgvector-schema-v0.md`、`teamDoc/GADoc/artifacts/postgres/001_schema_v0.sql`。
- 当前边界：不引入 SQLAlchemy/Alembic 依赖，不连接真实数据库执行 migration；本步骤提供可由 `psql` 执行的 package migration 和 compose job。

### 2. 红灯测试设计

- 新增 `tests/team_cloud/test_postgres_migrations.py`，覆盖：
  - package 内存在 `001_schema_v0.sql`，且与 P0-08 artifact 一致。
  - migration 包含 pgcrypto/vector extension 和 P1-04 core tables。
  - 每个 migration 有 rollback note。
  - `MigrationRunner.default()` 使用 package migration，并输出 checksum。
  - psql apply command 使用 `ON_ERROR_STOP=1`。
  - compose 包含 `team-migrate` job，且 `team-api` 依赖该 job 完成。
  - P1-04 GADoc 引用 migration、rollback 和 compose job。

### 3. 最小实现

- 机械提升 P0-08 SQL artifact 到 `team_cloud/sql_migrations/001_schema_v0.sql`，保持内容完全一致。
- 新增 rollback note：`team_cloud/sql_migrations/001_schema_v0.rollback.md`。
- 增强 `team_cloud.migrations`：
  - `Migration` 增加 `checksum_sha256`。
  - `MigrationRunner.default()` 改为读取 package migration。
  - `dry_run()` 输出 migration 名称和 SHA-256 checksum。
  - 新增 `psql_apply_commands()` 和 `apply_psql()`。
- 更新 `pyproject.toml` package data，打包 SQL migration 和 rollback note。
- 更新 `deploy/team-cloud/compose.yaml`：
  - 新增 `team-migrate` job。
  - `team-api` 依赖 `team-migrate` `service_completed_successfully`。
- 新增 `teamDoc/GADoc/P1-04-postgres-base-migrations.md`。

## 验证记录

- 红灯：`scripts/run_tests.sh tests/team_cloud/test_postgres_migrations.py`
  - 结果：`7 tests failed`。
  - 失败点：缺少 package SQL migration、rollback note、runner checksum/apply API、compose `team-migrate` job 和 P1-04 GADoc。
- 绿灯：`scripts/run_tests.sh tests/team_cloud/test_postgres_migrations.py`
  - 结果：`7 tests passed, 0 failed`。
- 回归：`scripts/run_tests.sh tests/test_project_metadata.py tests/team_cloud/test_config_secret_management.py tests/team_cloud/test_skeleton.py tests/team_cloud/test_local_compose_stack.py tests/team_cloud/test_postgres_migrations.py`
  - 结果：`33 tests passed, 0 failed`。
- Ruff：`venv/bin/ruff check team_cloud tests/team_cloud`
  - 结果：`All checks passed!`。
- 语法检查：`venv/bin/python -m compileall -q team_cloud`
  - 结果：退出码 0。
- Compose 解析：`docker compose -f deploy/team-cloud/compose.yaml --env-file deploy/team-cloud/.env.example config >/tmp/hermes-team-cloud-compose-config.yaml && wc -l /tmp/hermes-team-cloud-compose-config.yaml`
  - 结果：Docker Compose config 成功，标准化输出 `533` 行。
