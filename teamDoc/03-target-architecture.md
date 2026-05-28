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
  ├─ Team API (Go net/http service, team_cloud/)
  ├─ Team Cloud Admin Dashboard (Next.js static export, /dashboard/)
  ├─ Auth Middleware (Casdoor JWT validation)
  ├─ Authorization Gateway (SpiceDB client)
  ├─ Memory API
  ├─ Team Parent Soul API
  ├─ Session API
  ├─ Admin/Data Management API
  ├─ Backup/Export API
  ├─ Worker Queue (DB-backed outbox + workers)
  └─ Audit/Observability

Data Plane
  ├─ PostgreSQL
  │   ├─ product schema
  │   ├─ cloud sessions/messages/tools
  │   ├─ team memory_items / memory_embeddings
  │   ├─ audit_events / outbox_events
  │   └─ pgvector indexes
  └─ Optional MinIO/S3-compatible object store
      ├─ team-memory-backups
      └─ team-soul-backups

Hermes Runtime Plane
  ├─ hermes-agent workers
  ├─ TeamMemoryProvider
  ├─ Local personal memory + local SOUL.md + /cloud-backup
  ├─ TeamToolPolicyHook
  ├─ TeamGateway identity resolver
  ├─ Existing tools / skills / Gateway adapters
  └─ Session migration and runtime event bridge
```

## 2. 核心边界

| 边界 | 规则 |
| --- | --- |
| AuthN | 只信任 Casdoor token、Casdoor JWKS 和 Team Cloud Go 登录后签发的 Redis session token |
| AuthZ | 所有资源级访问必须经过 SpiceDB；数据库 ACL shadow 只做缓存 |
| Memory | Team Cloud PostgreSQL 中 `memory_items` 只承载团队记忆；个人记忆留在本地 Hermes profile |
| Soul | Team Cloud Go 管理团队父人格；本地 `SOUL.md` 是成员子人格；team mode 下保存本地人格会由 Hermes Agent 调用当前模型供应商合并 effective soul，冲突以团队父人格为准 |
| Backup | Team Cloud 团队记忆备份以 memory id 做幂等恢复；团队父人格备份以 org/team active soul 做幂等恢复；MinIO/S3 仅为可选对象存储 |
| Runtime | Hermes worker 不直接决定团队权限，只执行 Team Cloud 注入的上下文和 hook |
| Admin | Team Cloud 云端管理台随 `team_cloud` 部署，首次初始化后管理 API 需要 Dashboard session token 或 Casdoor 登录 + SpiceDB check |
| Local Hermes UI | 本地 Hermes dashboard/CLI/Desktop 不承载团队云端管理，只通过 Hermes Agent Bridge 保存远程 Team Cloud 地址、token 和个人本地运行配置 |

## 3. Team API

职责：

- 验证 Casdoor JWT，解析 `sub`、`email`、`groups`、`roles`、`tenant` claims。
- 将 Casdoor identity 映射为 `member_id`。
- 处理组织、团队、项目、成员、邀请、服务账号。
- 调用 SpiceDB 做 permission check。
- 创建 agent run，分发到 Hermes runtime worker。
- 暴露会话、记忆、文档、备份、审计、导出和删除 API。

实现说明：

- 首次上线的 Team API 由 `team_cloud/` Go 服务提供；旧 Python 服务端已经删除，不作为部署目标或参考执行路径。
- Go 服务默认暴露 health/readiness/metrics、`/dashboard/` 静态管理台、bootstrap API、组织团队成员 API、团队记忆 API、团队父人格 API、review queue、团队记忆备份 API 和团队父人格备份 API。
- `TEAM_CLOUD_DATABASE_URL` 存在时使用 PostgreSQL `tcg_*` schema；为空时使用内存后端，仅用于开发测试。
- `team_cloud/dashboard/` 是 Team Cloud 管理页面唯一归属，包含首次初始化、超级管理员创建、团队成员、只读角色权限说明、记忆治理、团队父人格治理、团队级备份管理和审计视图。
- Hermes Desktop 可以打开 Dashboard URL，但不复制 Dashboard 功能，也不直连 Team Cloud 业务 API；Desktop 只调用 Hermes Agent CLI/API Bridge。

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
POST /v1/memory/{id}/disable
GET  /v1/memory/review
POST /v1/memory/review/{id}/approve
POST /v1/memory/observations
```

Go Team Cloud 首发版中，`DELETE /v1/memory/{id}` 对 Dashboard 记忆治理表示硬删除；停用记忆使用 `POST /v1/memory/{id}/disable`，落库为 `archived`。团队记忆来源通过 `source_type=auto_extracted/admin_created`、`source_member_id` 和 `created_by_member_id` 标识。CLI 显式新增团队记忆走 `team_memory_add`，写入 `status=active`；`/v1/memory/observations` 只保存可供后续抽取的 observation，Go 首发服务端不内置常驻 extraction worker。

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

## 7. 对象存储数据流

Team Cloud 服务端不再把 MinIO 作为必备组件。只有启用团队记忆或团队父人格备份对象存储时，才需要配置 S3/MinIO endpoint、bucket、access key 和加密 key；否则团队备份可保存在 PostgreSQL backup job snapshot 中。个人记忆和本地人格备份由本地 Hermes CLI `/cloud-backup memory|soul` 直接写入用户指定的 MinIO/S3-compatible 地址，不进入 Team Cloud 管理面。

Team Cloud 可选对象桶：

```text
hermes-team-memory-backups
hermes-team-soul-backups
```

对象 key 约定：

```text
org/{org_id}/team-memory/{yyyy}/{mm}/{backup_id}.jsonl.enc
org/{org_id}/team-soul/{yyyy}/{mm}/{backup_id}.json.enc
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
- `team_memory_add` 处理显式新增 active 团队记忆。
- `team_memory_propose` 处理待审核候选。
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
