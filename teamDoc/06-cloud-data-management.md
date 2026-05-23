# 06. 云端数据管理与 MinIO 备份方案

GA 产品必须把云端数据管理做成一等能力，而不是只提供数据库表和后台脚本。本方案中 PostgreSQL 保存 canonical data，MinIO 保存对象、导出包和个人记忆备份，SpiceDB 控制资源访问，Casdoor 控制登录身份。

## 1. 管理对象

管理台至少覆盖：

- Organizations。
- Teams / Projects。
- Members / Roles / Service Accounts。
- Gateway External Identities。
- Sessions / Messages / Tool Calls。
- Personal Memory。
- Team Shared Memory。
- Memory Review Queue。
- Documents / Knowledge Sources。
- Personal Backup Policies。
- Backup / Export / Restore Jobs。
- API Tokens。
- SpiceDB Permission Explorer。
- Audit Logs。
- Usage / Cost / Quotas。
- Data Retention / Deletion Requests。

## 2. 会话和消息管理

数据表：

```text
cloud_sessions
cloud_messages
cloud_tool_calls
cloud_session_events
agent_runs
agent_run_events
```

功能：

- 按 org/team/project/member/platform/model/status 过滤。
- 全文搜索和时间范围过滤。
- 查看工具调用、审批记录、token/cost、memory IDs。
- 从会话生成 team_shared 候选记忆。
- 导出会话为 JSONL/Markdown。
- 删除会话并异步清理关联 embedding 和对象。

权限：

- `session.read`：本人、参与者、项目可读成员。
- `session.delete`：owner 或项目管理员。
- `session.export`：owner 或项目管理员，组织导出需 Admin。

## 3. 记忆管理

Personal Memory 页面：

- 成员只能默认看自己的 personal memory。
- 支持搜索、编辑、删除、备份、恢复、导出。
- 支持查看来源和版本 diff。
- 支持暂停自动写入和设置保留策略。

Team Shared Memory 页面：

- 按 team/project/type/sensitivity/status 过滤。
- 支持审核、发布、归档、恢复、合并、标记过期。
- 支持查看来源会话、来源文档和 reviewer。
- 支持批量重新 embedding。

Review Queue：

- 候选内容、来源、置信度、风险标记。
- approve/reject/edit-before-approve。
- 审核 SLA 和积压告警。

## 4. 文档和知识库

PostgreSQL：

```text
documents
document_versions
document_chunks
document_embeddings
document_ingestion_jobs
document_permissions
```

MinIO：

```text
org/{org_id}/documents/{document_id}/versions/{version_id}/source.bin
org/{org_id}/documents/{document_id}/exports/{export_id}.zip
```

原则：

- 文档是源材料，记忆是抽取后的长期事实/偏好/决策。
- 文档权限通过 SpiceDB 继承 project/team。
- 文档 chunk 可参与召回，但必须和 memory block 分开标注。

## 5. MinIO 对象模型

桶：

```text
hermes-personal-backups
hermes-org-exports
hermes-attachments
hermes-document-sources
hermes-restore-staging
```

统一 manifest：

```sql
create table object_manifests (
  id uuid primary key,
  org_id uuid not null,
  owner_member_id uuid null,
  bucket text not null,
  object_key text not null,
  object_type text not null,
  size_bytes bigint not null,
  checksum_sha256 text not null,
  encryption_key_id text not null,
  retention_until timestamptz null,
  legal_hold boolean not null default false,
  status text not null,
  created_by uuid null,
  created_at timestamptz not null,
  deleted_at timestamptz null,
  unique(bucket, object_key)
);
```

对象 key：

```text
org/{org_id}/member/{member_id}/personal-memory/{yyyy}/{mm}/{backup_id}.jsonl.enc
org/{org_id}/exports/{export_id}/manifest.json
org/{org_id}/attachments/{attachment_id}/blob
org/{org_id}/documents/{document_id}/source/{version_id}.bin
org/{org_id}/restore/{restore_job_id}/staging.jsonl.enc
```

## 6. 个人记忆定时备份

成员可配置：

```text
enabled
cadence = daily | weekly | monthly
include_archived = false
include_deleted = false
include_embeddings = false
retention_count = 7 | 30 | custom
encryption = org_managed | user_passphrase
notification = email | in_app | webhook
```

备份流程：

```text
1. scheduler 找到 due backup policy。
2. SpiceDB check backup.restore/read ownership。
3. PostgreSQL repeatable read transaction 导出 memory_items + events manifest。
4. 生成 JSONL + manifest。
5. 加密并计算 checksum。
6. 上传 MinIO。
7. 写 object_manifests 和 backup_jobs。
8. 写 audit event。
9. 通知成员。
```

恢复流程：

```text
1. 成员选择备份包。
2. Team API 生成 restore preview。
3. 检查冲突：same checksum、same normalized_content、newer version。
4. 用户选择 skip/merge/overwrite/archive-old。
5. 写 restore job。
6. staging -> memory_items。
7. 重建 embedding。
8. 写 memory_events 和 audit。
```

## 7. 组织导出与删除

组织导出：

- 包含 org/team/project/member metadata。
- 包含 sessions/messages/tool_calls。
- 包含 memory_items/memory_events。
- 包含 documents manifest，不默认包含所有附件内容，可选 include blobs。
- 包含 SpiceDB relationships snapshot。
- 包含 Casdoor subject 映射，不导出密码或 Casdoor secret。

删除请求：

```text
data_deletion_requests
  id
  org_id
  requester_member_id
  target_type = member | project | org
  target_id
  mode = anonymize | soft_delete | hard_delete
  approval_status
  scheduled_at
  completed_at
```

硬删除顺序：

```text
disable access
export if requested
delete/mark SpiceDB relationships
soft delete PostgreSQL rows
delete MinIO objects
hard delete PostgreSQL rows after retention
write final audit
```

## 8. 安全与隐私

最低要求：

- 所有表带 `org_id`。
- PostgreSQL query 必须强制 tenant scope。
- 可启用 RLS 防御代码缺陷。
- MinIO object key 带 org/member 前缀。
- 所有下载使用短期 signed URL。
- 日志脱敏，不记录 token、secret、完整 personal memory。
- secret detector 阻止密钥写入长期记忆。
- break-glass 读取个人记忆或备份必须双人审批。

## 9. 观测与告警

指标：

- Casdoor token validation failure。
- SpiceDB check latency/deny/error。
- memory prefetch latency。
- pgvector query latency。
- backup job success/failure。
- MinIO upload/download latency。
- outbox lag。
- review queue backlog。
- cross-tenant deny count。

告警：

- SpiceDB unavailable。
- Casdoor JWKS refresh failure。
- outbox dead letter。
- backup failure > 3 次。
- MinIO checksum mismatch。
- personal memory cross-member access attempt。
- destructive tool approval bypass attempt。

## 10. RPO/RTO

| 数据 | RPO | RTO | 机制 |
| --- | ---: | ---: | --- |
| PostgreSQL | <= 15 分钟 | <= 4 小时 | WAL/PITR、每日全量、恢复演练 |
| SpiceDB | <= 15 分钟 | <= 4 小时 | 关系快照 + PostgreSQL outbox 重放 |
| MinIO | <= 1 小时 | <= 4 小时 | bucket replication 或定时 mirror |
| Casdoor 配置 | <= 1 小时 | <= 4 小时 | 配置导出、数据库备份 |
| 个人备份 | 按用户 cadence | <= 4 小时 | MinIO object + manifest restore |

## 11. GA 验收

- 成员可自助配置个人记忆定时备份。
- 备份包可下载、校验、恢复、删除。
- 组织导出可在空环境回灌核心数据。
- 删除请求有审批、执行、审计和失败重试。
- MinIO 对象和 PostgreSQL manifest 无孤儿对象。
- SpiceDB relationship 快照可重建授权状态。
