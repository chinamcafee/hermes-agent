# 04. PostgreSQL/pgvector 双层长期记忆设计

本方案把 PostgreSQL 中的 `memory_items` 作为唯一 canonical memory，pgvector 作为默认向量检索能力。个人记忆和团队共同记忆是数据库 schema、权限关系、召回策略、备份策略中的一等概念。

## 1. Scope 定义

```text
personal
  org_id
  subject_member_id
  owner_user_id
  visibility = self
  optional backup_policy_id

team_shared
  org_id
  team_id
  optional project_id
  visibility = team | project | org
  review_status = pending | approved | rejected
```

GA 默认只承诺两级记忆：

- `personal`：成员个人长期偏好、事实、工作习惯、明确要求记住的信息。
- `team_shared`：团队规范、项目决策、流程、公共事实、共享知识。

扩展 scope 如 `project_shared`、`channel_shared` 可以通过 `team_shared + project_id/channel_id` 表达，不新增第一版产品概念。

## 2. PostgreSQL Schema

```sql
create table memory_items (
  id uuid primary key,
  org_id uuid not null,
  scope text not null check (scope in ('personal', 'team_shared')),
  subject_member_id uuid null,
  owner_user_id uuid null,
  team_id uuid null,
  project_id uuid null,
  channel_id uuid null,
  title text null,
  content text not null,
  normalized_content text not null,
  summary text null,
  memory_type text not null,
  source_type text not null,
  source_session_id uuid null,
  source_message_ids uuid[] not null default '{}',
  source_document_id uuid null,
  created_by uuid null,
  reviewed_by uuid null,
  confidence double precision not null default 0,
  importance double precision not null default 0,
  status text not null check (status in ('active','pending_review','archived','deleted','rejected')),
  sensitivity text not null check (sensitivity in ('normal','pii','secret','restricted')),
  version int not null default 1,
  checksum_sha256 text not null,
  expires_at timestamptz null,
  created_at timestamptz not null,
  updated_at timestamptz not null,
  deleted_at timestamptz null,
  constraint memory_scope_subject_ck check (
    (scope = 'personal' and subject_member_id is not null and team_id is null)
    or
    (scope = 'team_shared' and team_id is not null)
  )
);

create table memory_embeddings (
  memory_id uuid not null references memory_items(id),
  org_id uuid not null,
  embedding_model text not null,
  embedding vector(1536) not null,
  embedding_hash text not null,
  dimensions int not null,
  created_at timestamptz not null,
  primary key(memory_id, embedding_model)
);

create table memory_events (
  id uuid primary key,
  org_id uuid not null,
  memory_id uuid not null,
  actor_member_id uuid null,
  event_type text not null,
  before jsonb null,
  after jsonb null,
  reason text null,
  request_id text null,
  created_at timestamptz not null
);

create table memory_observations (
  id uuid primary key,
  org_id uuid not null,
  team_id uuid null,
  project_id uuid null,
  member_id uuid not null,
  session_id uuid not null,
  turn_id uuid not null,
  user_content text not null,
  assistant_content text not null,
  tool_summaries jsonb not null default '[]',
  status text not null default 'pending',
  created_at timestamptz not null,
  processed_at timestamptz null
);

create table memory_review_items (
  id uuid primary key,
  org_id uuid not null,
  candidate_memory_id uuid not null references memory_items(id),
  team_id uuid not null,
  project_id uuid null,
  proposed_by uuid null,
  reviewer_id uuid null,
  status text not null,
  reason text null,
  created_at timestamptz not null,
  reviewed_at timestamptz null
);
```

## 3. 索引策略

```sql
create index memory_items_org_scope_status_idx
  on memory_items(org_id, scope, status);

create index memory_items_personal_idx
  on memory_items(org_id, subject_member_id, status, updated_at desc)
  where scope = 'personal';

create index memory_items_team_idx
  on memory_items(org_id, team_id, project_id, status, updated_at desc)
  where scope = 'team_shared';

create index memory_items_type_sensitivity_idx
  on memory_items(org_id, memory_type, sensitivity);

create index memory_embeddings_hnsw_idx
  on memory_embeddings
  using hnsw (embedding vector_cosine_ops);
```

GA 默认：

- 小规模和中规模租户使用 HNSW。
- bulk import 可先禁用或延后创建 HNSW，导入完成后重建。
- 每次 embedding 模型切换都保留旧模型 embedding 到迁移完成。

## 4. 写入策略

### Personal memory

默认自动写入，但必须满足：

- 当前 actor 是 `subject_member_id` 本人。
- 不包含 secret。
- 不来自召回上下文。
- 不是临时状态或一次性任务。
- SpiceDB check `memory.personal.write` 通过。

写入状态：

```text
normal/pii -> active
secret/restricted -> rejected 或 pending_review
low confidence -> pending_review
```

### Team shared memory

默认审核后发布：

```text
conversation/document/tool observation
  -> candidate extraction
  -> memory_items(status=pending_review, scope=team_shared)
  -> memory_review_items
  -> curator approve
  -> SpiceDB relationship write
  -> status=active
```

允许自动发布的来源：

- 项目文档 ingestion。
- 经过管理员标记的 trusted channel。
- CI/CD 或 connector 写入的结构化知识。
- Admin/Memory Curator 显式调用。

## 5. 召回流程

```text
TeamMemoryProvider.prefetch(query)
  -> POST /v1/memory/prefetch
  -> Team API verifies actor
  -> build personal candidate query
  -> build team candidate query
  -> pgvector semantic search
  -> SQL metadata filtering
  -> SpiceDB batch check
  -> rerank
  -> redact by sensitivity
  -> return formatted memory block
```

召回块格式：

```markdown
## Personal Memory
- [preference][normal][m:...] ...

## Team Shared Memory
- [decision][team:backend][m:...] ...
```

安全要求：

- personal memory 永远只按 `subject_member_id = current_member_id` 查询。
- team_shared 必须按 `org_id/team_id/project_id` 过滤，并通过 SpiceDB。
- 召回结果 ID 记录到 `memory_read_events`。
- 召回内容带 context fence，防止再次写回记忆。

## 6. Ranking

```text
score =
  0.50 * semantic_similarity
  + 0.15 * importance
  + 0.10 * recency
  + 0.10 * source_trust
  + 0.10 * scope_match
  + 0.05 * explicit_pin
  - sensitivity_penalty
  - staleness_penalty
  - contradiction_penalty
```

默认 top-k：

- personal：最多 8 条。
- team_shared：最多 12 条。
- restricted：默认不注入，只返回需要审批/权限不足标记。

## 7. TeamMemoryProvider 工具

> 2026-05-24 更新：Team Cloud GA 主路径只管理团队记忆。个人记忆不进入 Team Cloud，`team_memory_remember` 和 `team_memory_backup_now` 已退役；本地个人记忆备份统一使用 `/cloud-backup memory`。

```text
team_memory_search
  query
  scope = team_shared
  team_id?
  project_id?
  limit

team_memory_add
  content
  memory_type
  sensitivity?
  source_type = admin_created

team_memory_propose
  content
  team_id
  project_id?
  reason

team_memory_promote
  memory_id
  target_team_id
  target_project_id?
  reason

team_memory_forget
  memory_id
  reason
```

所有工具返回 JSON string，写操作必须先做权限 check 并写 audit。CLI 显式“创建/增加团队记忆”走 `team_memory_add`；自动抽取走 `team_memory_propose` 或服务端 review flow。

## 8. 防污染机制

必须实现：

- context fencing：召回块、系统提示、工具结果摘要都不能原样写回。
- trivial filter：过滤寒暄、短期状态、重复确认。
- PII/secret detector：识别密钥、token、身份证、手机号、邮箱等。
- duplicate detector：checksum + semantic near duplicate。
- contradiction detector：新旧事实冲突进入 review。
- stale decay：过期策略和手动 mark stale。
- source trace：每条记忆可追溯到会话、消息、文档或导入任务。

## 9. 个人记忆备份触发

个人记忆备份由成员自行管理：

```text
backup_policy
  enabled
  cadence = daily | weekly | monthly
  include_embeddings = false by default
  retention_count
  encrypt_with = org_kms | user_passphrase
```

流程：

```text
schedule
  -> SpiceDB check backup.restore/read ownership
  -> export personal memory JSONL
  -> encrypt
  -> upload to MinIO
  -> write object_manifest
  -> write audit
  -> notify member
```

## 10. GA 验收

- 个人记忆跨成员召回测试 100% 拒绝。
- 团队记忆跨 org 召回测试 100% 拒绝。
- 每条 active team_shared memory 有来源和审核路径。
- 每次敏感记忆读取都有 audit。
- pgvector index rebuild 有 runbook。
- embedding 模型切换可灰度，可回滚。
- 用户可自助备份、下载、恢复和删除个人记忆。
