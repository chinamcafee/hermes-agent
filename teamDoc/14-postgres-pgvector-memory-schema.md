# 14. PostgreSQL/pgvector 记忆库详细 Schema

## 1. Schema 分层

```text
identity tables
  users / organizations / members / teams / projects

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

- `team_cloud_go/` 使用 `tcg_*` 表承载首发服务端的组织、成员、记忆、review 和备份策略数据。
- 由于 Python Team Cloud 未上线，Go 版不需要兼容 Python 版 UUID schema 的线上迁移；首次部署直接初始化 Go schema。
- pgvector 详细 embedding schema 仍是长期目标，Go 版当前先提供 canonical memory CRUD、状态流转和 text prefetch，后续可在 `tcg_memory_items` 旁路扩展 embedding 表。

## 2. memory_items 字段约束

| 字段 | 要求 |
| --- | --- |
| `org_id` | 所有查询必带 |
| `scope` | 只允许 `personal` 或 `team_shared` |
| `subject_member_id` | personal 必填，team_shared 为空 |
| `team_id` | team_shared 必填 |
| `status` | active/pending_review/archived/deleted/rejected |
| `sensitivity` | normal/pii/secret/restricted |
| `checksum_sha256` | 去重和备份校验 |

## 3. pgvector 查询模板

Personal：

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
