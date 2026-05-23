# P0-08 PostgreSQL/pgvector schema v0

日期：2026-05-22
状态：Validated for P0 execution
前置：`P0-07 SpiceDB schema v0`

## 目标

产出 Team Cloud PostgreSQL/pgvector schema v0，覆盖身份、权限 outbox、会话、双层记忆、个人备份、对象 manifest 和审计。该 schema 是 P1 migration 的输入，不直接修改 Hermes runtime。

## 工件

| 工件 | 用途 |
| --- | --- |
| [001_schema_v0.sql](artifacts/postgres/001_schema_v0.sql) | PostgreSQL schema v0。 |
| [schema-v0-smoke.sql](artifacts/postgres/schema-v0-smoke.sql) | 最小数据路径、pgvector extension 和约束 smoke test。 |

## Schema 分层

| 层 | 表 |
| --- | --- |
| identity | `team_cloud_users`、`organizations`、`members`、`teams`、`projects`、`external_identities`、`service_accounts`、`api_tokens` |
| conversation/runtime | `cloud_sessions`、`cloud_messages`、`cloud_tool_calls` |
| memory | `memory_items`、`memory_embeddings`、`memory_events`、`memory_observations`、`memory_review_items` |
| authz | `spicedb_outbox`、`permission_cache` |
| backup/object | `backup_policies`、`backup_jobs`、`restore_jobs`、`object_manifests` |
| audit | `audit_events` |

## 双层记忆约束

`memory_items.scope` 只允许：

- `personal`：必须有 `subject_member_id`，不能有 `team_id`。
- `team_shared`：必须有 `team_id`，不能有 `subject_member_id`。

所有 memory 查询必须带 `org_id`。schema v0 通过 partial index 支持：

- personal: `(org_id, subject_member_id, status, sensitivity)`
- team_shared: `(org_id, team_id, status, sensitivity)`

## pgvector 冻结

- schema 启用 `vector` extension。
- `memory_embeddings.embedding` 使用 `vector(1536)`。
- `embedding_model` 和 `embedding_dim` 写入每行，为后续 embedding 维度迁移留出新列/新表路径。
- 默认 HNSW cosine index：`idx_memory_embeddings_hnsw`。

## 权限和备份路径

- `spicedb_outbox` 保存 relationship mutation，使用 `idempotency_key` 防重复。
- `permission_cache` 仅作性能优化，不作为最终权限真相。
- `object_manifests` 保存 MinIO bucket/key/checksum/encryption/status。
- `backup_policies`、`backup_jobs`、`restore_jobs` 支撑个人记忆定时备份、预览和恢复。
- `audit_events` 记录身份、权限、记忆、备份和工具事件。

## 验证命令

```bash
docker run -d --rm --name hermes-p0-08-postgres \
  -e POSTGRES_PASSWORD=postgres \
  pgvector/pgvector:0.8.2-pg18-trixie

docker exec -i hermes-p0-08-postgres psql -U postgres -v ON_ERROR_STOP=1 \
  < teamDoc/GADoc/artifacts/postgres/001_schema_v0.sql

docker exec -i hermes-p0-08-postgres psql -U postgres -v ON_ERROR_STOP=1 \
  < teamDoc/GADoc/artifacts/postgres/schema-v0-smoke.sql
```

验证覆盖：

- `vector` extension 可创建并返回版本。
- identity/team/project/session 最小链路可插入。
- personal memory、team_shared memory、embedding、event、observation 可插入。
- personal backup object manifest、policy、job 可插入。
- `spicedb_outbox` 和 `audit_events` 可插入。
- personal memory scope 约束拒绝缺少 `subject_member_id` 的非法记录。

## P1 影响

- `P1-04 PostgreSQL 基础迁移` 必须把本文 SQL 转换为 Alembic migration。
- `P1-11 Relationship outbox` 必须使用 `spicedb_outbox.idempotency_key`。
- `P2-01 记忆迁移表` 必须保持 `memory_items` personal/team_shared 约束。
- `P3-05 Personal backup policy` 必须基于 `backup_policies` 和 `backup_jobs`。
- `P3-16 Audit 高级能力` 必须扩展 `audit_events` 索引和 retention。
