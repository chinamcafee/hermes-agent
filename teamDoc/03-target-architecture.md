# 03. GA 目标架构

## 1. 架构总览

```text
User Entry
  ├─ Team Web Console
  ├─ OpenAI-compatible API clients
  ├─ Telegram / Slack / Discord / Feishu / WeCom
  └─ Webhooks / enterprise integrations

Identity Plane
  └─ Casdoor
      ├─ OIDC/OAuth2/JWT
      ├─ SAML/LDAP/SCIM federation
      ├─ MFA / password / external IdP
      └─ user/group/application lifecycle

Authorization Plane
  └─ SpiceDB
      ├─ org/team/project/member relationships
      ├─ session/memory/document/tool permissions
      ├─ permission check / lookup / explain
      └─ schema validation in CI

Team Cloud Control Plane
  ├─ Team API (Go net/http service, team_cloud_go/)
  ├─ Team Cloud Admin Dashboard (Next.js static export, /dashboard/)
  ├─ Auth Middleware (Casdoor JWT validation)
  ├─ Authorization Gateway (SpiceDB client)
  ├─ Memory API
  ├─ Session API
  ├─ Admin/Data Management API
  ├─ Backup/Export API
  ├─ Worker Queue (DB-backed outbox + workers)
  └─ Audit/Observability

Data Plane
  ├─ PostgreSQL
  │   ├─ product schema
  │   ├─ cloud sessions/messages/tools
  │   ├─ memory_items / memory_embeddings
  │   ├─ audit_events / outbox_events
  │   └─ pgvector indexes
  └─ MinIO
      ├─ personal-memory-backups
      ├─ org-exports
      ├─ attachments
      ├─ document-sources
      └─ restore-staging

Hermes Runtime Plane
  ├─ hermes-agent workers
  ├─ TeamMemoryProvider
  ├─ TeamToolPolicyHook
  ├─ TeamGateway identity resolver
  ├─ Existing tools / skills / Gateway adapters
  └─ Session migration and runtime event bridge
```

## 2. 核心边界

| 边界 | 规则 |
| --- | --- |
| AuthN | 只信任 Casdoor token、Casdoor JWKS 和 Team Cloud service token |
| AuthZ | 所有资源级访问必须经过 SpiceDB；数据库 ACL shadow 只做缓存 |
| Memory | PostgreSQL 中 `memory_items` 是唯一 canonical memory |
| Backup | MinIO 对象必须有 PostgreSQL manifest、checksum、owner 和审计 |
| Runtime | Hermes worker 不直接决定团队权限，只执行 Team Cloud 注入的上下文和 hook |
| Admin | Team Cloud 云端管理台随 `team_cloud_go` 部署，管理 API 需要 service token 或 Casdoor 登录 + SpiceDB check |
| Local Hermes UI | 本地 Hermes dashboard/CLI 不承载团队云端管理，只保存远程 Team Cloud 地址、token 和个人本地运行配置 |

## 3. Team API

职责：

- 验证 Casdoor JWT，解析 `sub`、`email`、`groups`、`roles`、`tenant` claims。
- 将 Casdoor identity 映射为 `member_id`。
- 处理组织、团队、项目、成员、邀请、服务账号。
- 调用 SpiceDB 做 permission check。
- 创建 agent run，分发到 Hermes runtime worker。
- 暴露会话、记忆、文档、备份、审计、导出和删除 API。

实现说明：

- 首次上线的 Team API 由 `team_cloud_go/` 提供，Python `team_cloud/` 不作为部署目标。
- Go 服务默认暴露 health/readiness/metrics、`/dashboard/` 静态管理台、bootstrap API、组织团队成员 API、双层记忆 API、review queue 和个人备份策略 API。
- `TEAM_CLOUD_DATABASE_URL` 存在时使用 PostgreSQL `tcg_*` schema；为空时使用内存后端，仅用于开发测试。
- `team_cloud_go/dashboard/` 是 Team Cloud 管理页面唯一归属，包含首次初始化、超级管理员创建、组织/团队/成员、权限关系、记忆审核、备份策略和审计视图。

必须实现的中间件：

```text
RequestIdMiddleware
TenantResolutionMiddleware
CasdoorJwtMiddleware
MemberStatusMiddleware
SpiceDbAuthorizationMiddleware
AuditMiddleware
RateLimitMiddleware
```

请求上下文：

```text
request_context
  request_id
  org_id
  team_id
  project_id
  member_id
  casdoor_subject
  actor_type = human | service_account | system
  auth_method = web | api_token | gateway_binding
  permissions_cache_key
```

## 4. Casdoor 集成

Team Cloud 通过 OIDC 接入 Casdoor：

```text
1. Web Console 跳转 Casdoor authorize endpoint。
2. Casdoor 完成登录/MFA/federation。
3. Web Console 收到 code 并换 token。
4. Team API 校验 JWT 签名、issuer、audience、exp、nonce。
5. Team API upsert users/members。
6. Team API 将 membership 变化写入 SpiceDB outbox。
```

组织映射策略：

- Casdoor Organization 可以映射 Team Cloud `organization`。
- Casdoor User 映射 Team Cloud `user`。
- Casdoor Group 或 Role 映射 Team Cloud `membership` 和默认角色。
- Team Cloud 允许比 Casdoor 更细的 team/project membership。

## 5. SpiceDB 集成

Team Cloud 写入关系：

```text
organization:org1#owner@user:alice
organization:org1#member@user:bob
team:team1#parent@organization:org1
team:team1#member@user:bob
project:proj1#parent@team:team1
memory:mem1#owner@user:alice
memory:mem2#parent_team@team:team1
tool:terminal#allowed@role:developer
```

访问检查：

```text
check user:alice memory:mem1 read
check user:bob memory:mem2 read
check user:bob tool:terminal execute
check service_account:ci-bot project:proj1 run_agent
```

一致性要求：

- 业务表写入成功后，outbox 记录 SpiceDB relationship mutation。
- worker 以幂等 key 写 SpiceDB。
- API 读取时如果 relationship 未同步，危险操作默认 fail closed。
- 查询列表时先用 PostgreSQL 缩小集合，再批量 SpiceDB check。

## 6. Memory API

核心端点：

```text
POST /v1/memory/prefetch
GET  /v1/memory
POST /v1/memory
PATCH /v1/memory/{id}
DELETE /v1/memory/{id}
POST /v1/memory/{id}/promote
POST /v1/memory/{id}/archive
GET  /v1/memory/review
POST /v1/memory/review/{id}/approve
POST /v1/memory/observations
```

所有读取流程：

```text
1. 校验 Casdoor/Team Cloud actor。
2. PostgreSQL 按 org_id、scope、status、sensitivity 粗过滤。
3. pgvector 检索候选。
4. SpiceDB 批量校验 read/use permission。
5. sensitivity policy 降权或脱敏。
6. 格式化为 Personal Memory / Team Shared Memory 两段注入 Hermes。
7. 写入 memory_read audit event。
```

## 7. MinIO 数据流

对象桶：

```text
hermes-personal-backups
hermes-org-exports
hermes-attachments
hermes-document-sources
hermes-restore-staging
```

对象 key 约定：

```text
org/{org_id}/member/{member_id}/personal-memory/{yyyy}/{mm}/{backup_id}.jsonl.enc
org/{org_id}/exports/{export_id}/manifest.json
org/{org_id}/documents/{document_id}/source.bin
org/{org_id}/restore/{restore_job_id}/staging.jsonl.enc
```

所有对象必须在 PostgreSQL 中有 manifest：

```text
object_manifests
  id
  org_id
  owner_member_id
  bucket
  object_key
  object_type
  checksum_sha256
  encryption_key_id
  size_bytes
  status
  created_at
```

## 8. Hermes Runtime 集成

新增上下文：

```text
team_context
  org_id
  team_id
  project_id
  member_id
  actor_type
  roles
  source_platform
  external_identity_id
  authorization_session
```

`TeamMemoryProvider`：

- `initialize()` 接收 `team_context`。
- `prefetch()` 调 Memory API。
- `sync_turn()` 写 observations。
- `get_tool_schemas()` 暴露记忆管理工具。
- `handle_tool_call()` 对写操作先走 SpiceDB check。

`TeamToolPolicyHook`：

- 工具执行前按 tool risk 做 SpiceDB check。
- 高危工具要求 Hermes approval。
- 所有工具调用写 `cloud_tool_calls` 和 audit。

## 9. GA 非功能目标

| 类别 | GA 目标 |
| --- | --- |
| 可用性 | Team API 99.5% 起步，企业版目标 99.9% |
| RPO | PostgreSQL <= 15 分钟，MinIO <= 1 小时 |
| RTO | 单节点私有化 <= 4 小时，多节点 <= 1 小时 |
| 权限延迟 | SpiceDB check P95 <= 30ms，批量 check P95 <= 100ms |
| 记忆召回 | prefetch P95 <= 500ms，不含 LLM 首 token |
| 审计 | 管理操作、高危工具、敏感记忆读写 100% 留痕 |
| 隔离 | 跨 org、跨 member personal memory 0 泄漏 |
| 备份 | 个人记忆定时备份成功率 >= 99%，失败可重试可告警 |
