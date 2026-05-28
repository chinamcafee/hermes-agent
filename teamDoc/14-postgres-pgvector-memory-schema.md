# 14. PostgreSQL/pgvector 记忆库详细 Schema

## 1. Schema 分层

```text
identity tables
  users / organizations / members / projects

conversation tables
  cloud_sessions / cloud_messages / cloud_tool_calls

memory tables
  memory_items / memory_embeddings / memory_events
  memory_observations / memory_review_items

backup tables
  backup_policies / backup_jobs / restore_jobs / object_manifests

authz tables
  spicedb_outbox / permission_cache

audit tables
  audit_events
```

Go 服务端首次上线补充：

- `team_cloud/` 使用 `tcg_*` 表承载首发服务端的团队空间、成员、记忆、review 和备份策略数据。
- Go 首发版已退役独立 `tcg_teams` 工作组表；团队共享记忆以 `org_id` 作为团队级边界，`team_id` 仅作为历史兼容字段。
- 2026-05-24 边界调整后，Team Cloud GA 主路径只管理 `team_shared`。`personal` 字段和查询模板保留为历史参考与兼容材料；个人记忆由 Hermes 本地 profile 和 CLI `/cloud-backup memory` 管理，本地人格由 `/cloud-backup soul` 管理。
- 当前 Team Cloud 首次部署直接初始化 Go `tcg_*` schema；旧 Python schema 不再作为迁移来源。
- pgvector 详细 embedding schema 仍是长期目标，Go 版当前在 `tcg_memory_items.embedding vector(1536)` 提供向量召回，并在同表保存 Dashboard 记忆治理所需的来源字段。

## 2. memory_items 字段约束

| 字段 | 要求 |
| --- | --- |
| `org_id` | 所有查询必带 |
| `scope` | 只允许 `personal` 或 `team_shared` |
| `subject_member_id` | personal 必填，team_shared 为空 |
| `team_id` | Go 首发版历史兼容字段，team_shared 不再要求必填 |
| `status` | active/pending_review/archived/deleted/rejected |
| `sensitivity` | normal/pii/secret/restricted |
| `source_type` | team_shared 来源标签：`auto_extracted` 或 `admin_created` |
| `source_member_id` | 自动抽取记忆的来源成员 |
| `created_by_member_id` | 管理员创建记忆的创建者 |
| `checksum_sha256` | 去重和备份校验 |

## 3. pgvector 查询模板

Personal（历史参考，不属于 Team Cloud GA 主路径）：

```sql
select mi.*, 1 - (me.embedding <=> :query_embedding) as similarity
from memory_embeddings me
join memory_items mi on mi.id = me.memory_id
where mi.org_id = :org_id
  and mi.scope = 'personal'
  and mi.subject_member_id = :member_id
  and mi.status = 'active'
  and mi.sensitivity in ('normal', 'pii')
order by me.embedding <=> :query_embedding
limit :limit;
```

Team shared：

```sql
select mi.*, 1 - (me.embedding <=> :query_embedding) as similarity
from memory_embeddings me
join memory_items mi on mi.id = me.memory_id
where mi.org_id = :org_id
  and mi.scope = 'team_shared'
  and mi.team_id = any(:candidate_team_ids)
  and mi.status = 'active'
order by me.embedding <=> :query_embedding
limit :candidate_limit;
```

Team shared 结果返回前必须批量 SpiceDB check。

## 4. Migration 策略

- 所有迁移前向兼容。
- 新字段先 nullable，再 backfill，再 not null。
- embedding 维度变化走新 `embedding_model`。
- 大索引变更使用并发创建或维护窗口。
- 每个 migration 有 rollback note。

## 5. 数据质量任务

- duplicate merge。
- stale detector。
- contradiction review。
- orphan embedding cleanup。
- deleted memory hard purge。
- source trace integrity checker。
- SpiceDB relationship consistency checker。
