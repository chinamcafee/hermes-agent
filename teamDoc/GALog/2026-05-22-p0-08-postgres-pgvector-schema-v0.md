# GALog 2026-05-22 P0-08 PostgreSQL/pgvector schema v0

## 工作粒度

- 工作包：`P0-08 PostgreSQL/pgvector schema v0`
- 类型：数据模型 / 可执行 SQL 工件
- 执行日期：2026-05-22
- 执行者：Codex

## 输入依据

- `teamDoc/GAStep/02-phase-0-1-foundation-steps.md`
- `teamDoc/14-postgres-pgvector-memory-schema.md`
- `teamDoc/GADoc/adr/ADR-0003-postgres-pgvector-memory.md`
- `teamDoc/GADoc/P0-04-component-version-license-freeze.md`
- `teamDoc/GADoc/P0-05-local-topology-design.md`

## 产出

- 新增：`teamDoc/GADoc/artifacts/postgres/001_schema_v0.sql`
- 新增：`teamDoc/GADoc/artifacts/postgres/schema-v0-smoke.sql`
- 新增：`teamDoc/GADoc/P0-08-postgres-pgvector-schema-v0.md`

## 执行记录

1. 核对 P0-08 要求：schema 必须包含身份、权限 outbox、memory、backup、audit。
2. 将 `memory_items.scope` 约束为 `personal` 和 `team_shared` 两条互斥路径。
3. 增加 `memory_embeddings vector(1536)` 和 HNSW cosine index。
4. 增加 `spicedb_outbox`、`permission_cache`、`object_manifests`、`backup_policies`、`backup_jobs`、`restore_jobs`、`audit_events`。
5. 编写 smoke SQL，覆盖最小插入路径和非法 personal memory 约束负测。
6. 首次验证发现 PostgreSQL 不允许在 table-level unique constraint 中使用 `coalesce(...)` 表达式；已改为后置 unique index `idx_external_identities_unique_platform_user_team`。

## 决策摘要

1. PostgreSQL 是 canonical memory 和业务数据真相；pgvector 只作为派生向量索引。
2. `permission_cache` 只做优化，最终权限仍来自 SpiceDB。
3. 个人备份对象必须经过 `object_manifests` 记录 checksum/encryption/status。
4. `memory_embeddings` v0 固定 1536 维，后续模型升级通过新 migration 扩展。

## 验证计划

- 用 `pgvector/pgvector:0.8.2-pg18-trixie` 容器执行 schema SQL。
- 执行 smoke SQL，验证 extension、插入路径和 check constraint。
- 检查 schema 文件包含 P0-08 指定的 identity/authz/memory/backup/audit 表。
- 验证后更新 `progress-tracker.md` 中 `P0-08` 为 `Done`。

## 验证结果

```text
docker exec -i hermes-p0-08-postgres psql -U postgres -v ON_ERROR_STOP=1 < 001_schema_v0.sql
CREATE EXTENSION
...
CREATE INDEX

docker exec -i hermes-p0-08-postgres psql -U postgres -v ON_ERROR_STOP=1 < schema-v0-smoke.sql
BEGIN
INSERT 0 1
...
DO
 vector_version
----------------
 0.8.2
(1 row)
ROLLBACK

table_count=23
vector_version=0.8.2
```

临时容器 `hermes-p0-08-postgres` 已清理。

## 后续

- 进入 `P0-09 MinIO 备份模型 v0`。
