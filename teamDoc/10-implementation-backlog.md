# 10. GA 实施 Backlog

本文把 GA 方案拆成可排期任务。所有任务默认使用 Casdoor、SpiceDB、PostgreSQL/pgvector；MinIO/S3-compatible 作为团队记忆、团队父人格备份和 CLI 本地 memory/soul 备份的可选对象存储，不再设置临时身份或临时权限实现。

## 0. 架构冻结任务

- ADR-001：Casdoor AuthN 集成边界。
- ADR-002：SpiceDB AuthZ schema 和 relationship 生命周期。
- ADR-003：PostgreSQL/pgvector memory canonical schema。
- ADR-004：可选 MinIO/S3-compatible 备份对象模型。
- ADR-005：Hermes runtime 改动边界。
- 权限矩阵 v1。
- GA 验收矩阵 v1。
- 本地 compose stack。

## 1. 本地 GA 开发栈

```text
team_cloud/
  Dockerfile
  deploy/kubernetes/team-cloud-go.yaml
  dashboard/  # Next.js 静态管理台，随 Go 服务部署在 /dashboard/
  cmd/team-cloud-server/
  internal/httpapi/
  internal/store/postgres/

scripts/
  team-cloud-smoke.sh              # 当前 Go 服务端 + Dashboard smoke
  team-cloud-foundation-smoke.sh   # 当前 Hermes Agent / Team Cloud 回归
  team-cloud-isolation-smoke.sh    # 当前隔离和身份边界回归
  team-cloud-offline-bundle.sh     # 基于 team_cloud/ 的离线资料包
```

验收：

- `docker compose up` 后可登录 Casdoor。
- Go Team API 能通过 Dashboard session token 或 Casdoor/JWKS JWT 暴露管理和记忆 API。
- `/dashboard/` 能打开 Team Cloud Go Dashboard，并能在无预置 bootstrap token 的未初始化状态创建单团队空间和唯一超级管理员。
- Team API 能写 SpiceDB relationship。
- PostgreSQL 启用 pgvector。
- 如启用对象存储，MinIO/S3 bucket 可创建并通过 readiness。

## 2. Team Cloud Go service

```text
team_cloud/
  dashboard/
  cmd/team-cloud-server/main.go
  internal/config/config.go
  internal/httpapi/server.go
  internal/store/store.go
  internal/store/memory/store.go
  internal/store/postgres/schema.go
  internal/store/postgres/store.go
  deploy/kubernetes/team-cloud-go.yaml
```

旧 Team Cloud 服务端已经删除，后续不作为参考实现、测试入口或生产服务端。

## 3. Casdoor 集成任务

- OIDC client 配置文档。
- JWKS cache 和 key rotation。
- JWT validation middleware。
- Casdoor subject -> Team Cloud user mapping。
- Casdoor org/group -> organization/team/member sync。
- SCIM/webhook/reconcile worker。
- User disabled/suspended propagation。
- Login/logout audit。
- PAT 创建、撤销、hash 存储。
- Service account token。

测试：

- 错误 issuer/audience 拒绝。
- 过期 token 拒绝。
- disabled member 拒绝。
- group 变化同步 SpiceDB。

## 4. SpiceDB 集成任务

- `schema.zed` 初版。
- schema CI validate。
- permissions integration tests。
- `spicedb_outbox` 表。
- relationship writer worker。
- dead letter queue。
- permission check SDK。
- batch check SDK。
- lookup resources SDK。
- permission explorer API。
- 权限解释 UI。

关键 API：

```text
POST /v1/authz/check
POST /v1/authz/explain
GET  /v1/authz/resources
GET  /v1/authz/subjects
GET  /v1/authz/schema
```

## 5. PostgreSQL/pgvector 记忆任务

- migrations：memory_items。
- migrations：memory_embeddings。
- migrations：memory_events。
- migrations：memory_observations。
- migrations：memory_review_items。
- HNSW index。
- memory search SQL。
- personal/team_shared filters。
- embedding worker。
- duplicate detector。
- contradiction detector。
- secret/PII detector。
- review queue API。
- memory event audit。

API：

```text
POST /v1/memory/prefetch
GET  /v1/memory
POST /v1/memory
PATCH /v1/memory/{id}
DELETE /v1/memory/{id}
POST /v1/memory/{id}/promote
POST /v1/memory/{id}/disable
GET  /v1/memory/review
POST /v1/memory/review/{id}/approve
POST /v1/memory/observations
```

2026-05-24 Dashboard 记忆治理补充：Go Team Cloud 首发版中 `disable` 表示停用并写入 `archived`，`DELETE /v1/memory/{id}` 表示硬删除；团队记忆通过 `source_type` 区分自动抽取和管理员创建。

## 6. 备份任务

Team Cloud 团队记忆和团队父人格备份：

- 可选 bucket bootstrap。
- backup_policies 表复用 `member_id=__team_memory__` 表示团队记忆备份策略。
- backup_policies 表复用 `member_id=__team_soul__` 表示团队父人格备份策略；后续多资源备份可演进为显式 `resource_type=team_memory|team_soul`。
- backup_jobs 表保存团队记忆 snapshot、团队父人格 snapshot 和可选对象 manifest。
- restore preview/execute。
- team memory restore execute 按 memory id insert-or-update。
- team soul restore execute 按 org/team active soul insert-or-update，并递增版本。
- retention cleanup。

Hermes CLI 本地 memory/soul 备份：

- `/cloud-backup config` 保存用户对象存储配置。
- `/cloud-backup memory schedule` 和 `/cloud-backup soul schedule` 创建 resource-specific cron no-agent job。
- `/cloud-backup memory backup/history/restore` 处理当前 profile 的 `memories/` 文件。
- `/cloud-backup soul backup/history/restore` 处理当前 profile 的 `SOUL.md`。

API：

```text
GET  /v1/team-memory-backup-policy
PUT  /v1/team-memory-backup-policy
GET  /v1/team-soul-backup-policy
PUT  /v1/team-soul-backup-policy
GET  /v1/backups/team
POST /v1/backups/team/run
GET  /v1/backups/team/{id}
POST /v1/backups/team/{id}/restore-preview
POST /v1/backups/team/{id}/restore-execute
GET  /v1/backups/team-soul
POST /v1/backups/team-soul/run
POST /v1/backups/team-soul/{id}/restore-preview
POST /v1/backups/team-soul/{id}/restore-execute
```

## 7. Hermes 集成任务

### TeamMemoryProvider

- 当前实现位于 `agent/team_memory_provider.py`，由 Hermes Agent team mode first-party 挂载。
- `initialize(session_id, **kwargs)` 接收 `team_context`。
- `prefetch(query)` 调 Team Cloud Memory API，只召回 `team_shared`。
- `sync_turn()` 写 observations。
- `get_tool_schemas()` 暴露 `team_memory_search`、`team_memory_add`、`team_memory_propose`、`team_memory_promote`、`team_memory_forget`。
- `handle_tool_call()` 写操作固定 team scope，并由 Team Cloud API + AuthZ 层约束。

### TeamToolPolicyHook

- 当前实现位于 `agent/team_tool_policy.py`，`plugins/team_policy/` 只保留 env-gated lazy import 适配层。
- classify tool risk。
- permission mapping fail closed。
- high-risk tool 进入审批/拒绝路径。
- audit tool call。

### Core patch

- `AIAgent.__init__` 支持 `team_context`。
- API Server 支持可信 identity headers。
- Gateway 调 identity resolver。
- session key 增加 org/team prefix。

## 8. Team Web Console

页面：

- Login callback。
- Organization switcher。
- Members。
- Teams / Projects。
- Roles / Permission Explorer。
- Sessions。
- Team Shared Memory。
- Review Queue。
- Team Memory Backups。
- Documents。
- API Tokens / Service Accounts。
- Audit Logs。
- Usage / Quotas。
- Gateway Integrations。

每个页面要求：

- loading/error/empty states。
- permission denied state。
- audit-sensitive operation confirmation。
- filter/search/pagination。
- API error non-destructive display。

## 9. 数据治理任务

- Organization export。
- Member personal data export。
- Data deletion request。
- Hard delete worker。
- Anonymization worker。
- Retention policies。
- Audit export。
- SpiceDB relationship snapshot。
- MinIO orphan object scanner。

## 10. 测试任务

Hermes repo：

- `tests/hermes_cli/test_team_memory_provider.py`
- `tests/hermes_cli/test_team_cloud_cli.py`
- `tests/hermes_cli/test_team_memory_provider_tools.py`
- `tests/run_agent/test_memory_provider_init.py`
- `tests/gateway/test_gateway_team_identity_resolver.py`

Team Cloud repo：

- `team_cloud/internal/httpapi/*_test.go`
- `team_cloud/internal/store/*_test.go`
- `team_cloud/internal/authz/*_test.go`
- `team_cloud/internal/deploy/*_test.go`
- `team_cloud/dashboard/src/**/*.test.tsx`
- MinIO backup restore tests。
- permission matrix tests。
- audit tests。
- e2e Web/Gateway tests。

安全样例：

```text
org A / Alice personal: "I prefer Python"
org A / Bob query: "what language do I prefer?"
expected: Bob cannot see Alice memory

org A / team backend shared: "Use pnpm"
org B / team backend shared: "Use yarn"
expected: org A never sees org B memory

Guest calls terminal
expected: SpiceDB deny + audit event
```

## 11. 发布任务

- Docker Compose。
- Kubernetes manifest、minikube runbook 和 offline bundle。
- Offline image bundle。
- SBOM。
- License report。
- Backup/restore Runbook。
- Upgrade Runbook。
- Security guide。
- Admin guide。
- User guide。
- API reference。
- GA checklist sign-off。

## 12. Go Team Cloud 追加迁移任务

由于 Team Cloud 服务端首次上线改为 Go 实现，追加以下破坏性迁移任务：

- 在 `team_cloud/` 建立独立 Go module 和 `team-cloud-server` 二进制入口。
- 默认启动注册成员管理、团队记忆、review queue、团队记忆备份和团队父人格备份 API。
- 用 PostgreSQL `tcg_*` schema 作为 Go 服务生产持久化后端。
- 保留内存后端用于开发和单元测试，但禁止作为生产协作后端。
- 提供 Dockerfile 和 Kubernetes manifest，支持 Secret 注入 `TEAM_CLOUD_DATABASE_URL`、Redis 凭据；对象存储凭据仅在启用团队记忆对象备份时注入。
- 更新 `teamDoc/GAStep/06-team-cloud-go-service-steps.md`、进度追踪、release manual 和技术设计索引。

## 13. Go Team Cloud Dashboard 追加任务

- 在 `team_cloud/dashboard/` 建立 React + Next.js TypeScript 静态导出应用。
- Go 服务在 `/dashboard/` 托管 Dashboard 产物，并提供 SPA fallback。
- 新增 `/v1/bootstrap/status` 和 `/v1/bootstrap/super-admin`，支撑首次初始化、超级管理员创建和 owner relationship 写入。
- Dashboard 覆盖团队成员、只读角色权限说明、团队共享记忆治理、团队父人格治理、团队记忆/团队父人格备份管理、立即备份/恢复和审计查询。
- Dockerfile 使用 Node 22 Dashboard build stage + Go build stage，最终镜像包含 `/usr/share/team-cloud-go/dashboard`。
- Kubernetes manifest 注入 `TEAM_CLOUD_DASHBOARD_ENABLED=true` 和 `TEAM_CLOUD_DASHBOARD_DIR=/usr/share/team-cloud-go/dashboard`。
- 新增 minikube 本地 Kubernetes 部署手册，覆盖 PostgreSQL/pgvector、SpiceDB、可选 MinIO、Team Cloud Go + Dashboard 和本地 Hermes 连接。
