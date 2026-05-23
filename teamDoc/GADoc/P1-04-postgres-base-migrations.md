# P1-04 PostgreSQL 基础迁移

日期：2026-05-22
状态：Implemented
前置：`P0-08 PostgreSQL/pgvector schema v0`、`P1-01 Team Cloud repo/package 骨架`

## 目标

本步骤将 P0-08 PostgreSQL schema v0 提升为 Team Cloud package 内的可执行 migration。P1-04 的直接使用面是身份、组织、成员、团队、项目、审计和 SpiceDB outbox 基表；migration 文件保持与 P0-08 artifact 完全一致，因此同时包含后续 P2/P3 会继续使用的 memory、backup 和 object manifest 表。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/sql_migrations/001_schema_v0.sql` | package 内 canonical SQL migration，与 P0-08 artifact 一致。 |
| `team_cloud/sql_migrations/001_schema_v0.rollback.md` | rollback note，供本地开发和 pre-GA bootstrap 失败时使用。 |
| `team_cloud/migrations.py` | migration discovery、checksum、psql apply command。 |
| `deploy/team-cloud/compose.yaml` 中的 `team-migrate` | compose 启动时在 Team API 前执行 SQL migration。 |

## Runner 行为

- `MigrationRunner.default()` 从 package 内 `team_cloud/sql_migrations/` 读取 migration。
- `dry_run()` 返回 migration 名称和 SHA-256 checksum。
- `psql_apply_commands(database_url)` 生成 `psql --set ON_ERROR_STOP=1 <database_url> -f <migration>` 命令。
- `apply_psql(database_url)` 只封装 subprocess 调用，不保存或打印 database URL。

## Compose 顺序

`team-migrate` 依赖 `postgres-init` 成功完成，读取 `team_cloud_database_url` secret file，通过 `psql` 执行 `team_cloud/sql_migrations/001_schema_v0.sql`。`team-api` 依赖 `team-migrate` `service_completed_successfully`，避免 API 在 schema 未初始化时启动。

## 验证

```bash
scripts/run_tests.sh tests/team_cloud/test_postgres_migrations.py
scripts/run_tests.sh tests/test_project_metadata.py tests/team_cloud/test_config_secret_management.py tests/team_cloud/test_skeleton.py tests/team_cloud/test_local_compose_stack.py tests/team_cloud/test_postgres_migrations.py
docker compose -f deploy/team-cloud/compose.yaml --env-file deploy/team-cloud/.env.example config
```
