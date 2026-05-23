# 10. GA 实施 Backlog

本文把 GA 方案拆成可排期任务。所有任务默认使用 Casdoor、SpiceDB、PostgreSQL/pgvector、MinIO，不再设置临时身份或临时权限实现。

## 0. 架构冻结任务

- ADR-001：Casdoor AuthN 集成边界。
- ADR-002：SpiceDB AuthZ schema 和 relationship 生命周期。
- ADR-003：PostgreSQL/pgvector memory canonical schema。
- ADR-004：MinIO 个人备份、导出和恢复对象模型。
- ADR-005：Hermes runtime 改动边界。
- 权限矩阵 v1。
- GA 验收矩阵 v1。
- 本地 compose stack。

## 1. 本地 GA 开发栈

```text
team_cloud_go/
  Dockerfile
  deploy/kubernetes/team-cloud-go.yaml
  dashboard/  # Next.js 静态管理台，随 Go 服务部署在 /dashboard/
  cmd/team-cloud-server/
  internal/httpapi/
  internal/store/postgres/

deploy/team-cloud/  # P1-P5 历史验证资产，不作为首次上线 Team Cloud 服务端
  compose.yaml
  casdoor/
    app.conf
    init-data/
  spicedb/
    schema.zed
    test.yaml
  postgres/
    init.sql
    migrations/
  minio/
    buckets.sh
  web/
```

验收：

- `docker compose up` 后可登录 Casdoor。
- Go Team API 能通过 service token 暴露管理和记忆 API。
- `/dashboard/` 能打开 Team Cloud Go Dashboard，并能通过 service token 完成首次初始化。
- Team API 能写 SpiceDB relationship。
- PostgreSQL 启用 pgvector。
- MinIO 自动创建 buckets。

## 2. Team Cloud Go service

```text
team_cloud_go/
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

Python `team_cloud/` 是未上线参考实现，后续不作为生产服务端。

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
GET  /v1/memory/review
POST /v1/memory/review/{id}/approve
POST /v1/memory/observations
```

## 6. MinIO 个人备份任务

- bucket bootstrap。
- object_manifests 表。
- backup_policies 表。
- backup_jobs 表。
- restore_jobs 表。
- encrypted JSONL exporter。
- checksum manifest。
- signed URL。
- retention cleanup。
- restore preview。
- restore merge/overwrite/archive-old。
- backup notification。

API：

```text
GET  /v1/me/memory-backup-policy
PUT  /v1/me/memory-backup-policy
POST /v1/me/memory-backups/run
GET  /v1/me/memory-backups
GET  /v1/me/memory-backups/{id}/download-url
POST /v1/me/memory-backups/{id}/restore-preview
POST /v1/me/memory-backups/{id}/restore
DELETE /v1/me/memory-backups/{id}
```

## 7. Hermes 集成任务

### TeamMemoryProvider

- 新增 `plugins/memory/team_cloud/`。
- `initialize(session_id, **kwargs)` 接收 `team_context`。
- `prefetch(query)` 调 Team Cloud Memory API。
- `sync_turn()` 写 observations。
- `get_tool_schemas()` 暴露 memory tools。
- `handle_tool_call()` 写操作走 SpiceDB。

### TeamToolPolicyHook

- 新增 `plugins/team_policy/`。
- classify tool risk。
- SpiceDB check tool execute。
- require approval for high risk。
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
- Personal Memory。
- Team Shared Memory。
- Review Queue。
- Personal Backups。
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

- `tests/team_cloud/test_team_memory_provider.py`
- `tests/team_cloud/test_team_context.py`
- `tests/team_cloud/test_tool_policy_hook.py`
- `tests/team_cloud/test_api_server_identity_headers.py`
- `tests/team_cloud/test_gateway_identity_resolver.py`

Team Cloud repo：

- Casdoor JWT tests。
- SpiceDB schema tests。
- memory SQL scope tests。
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
- Helm chart。
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

- 在 `team_cloud_go/` 建立独立 Go module 和 `team-cloud-server` 二进制入口。
- 默认启动注册成员管理、双层记忆、review queue 和个人备份策略 API。
- 用 PostgreSQL `tcg_*` schema 作为 Go 服务生产持久化后端。
- 保留内存后端用于开发和单元测试，但禁止作为生产协作后端。
- 提供 Dockerfile 和 Kubernetes manifest，支持 Secret 注入 `TEAM_CLOUD_DATABASE_URL` 和 `TEAM_CLOUD_SERVICE_TOKEN`。
- 更新 `teamDoc/GAStep/06-team-cloud-go-service-steps.md`、进度追踪、release manual 和技术设计索引。

## 13. Go Team Cloud Dashboard 追加任务

- 在 `team_cloud_go/dashboard/` 建立 React + Next.js TypeScript 静态导出应用。
- Go 服务在 `/dashboard/` 托管 Dashboard 产物，并提供 SPA fallback。
- 新增 `/v1/bootstrap/status` 和 `/v1/bootstrap/super-admin`，支撑首次初始化、超级管理员创建和 owner relationship 写入。
- Dashboard 覆盖组织/团队/成员、权限关系写入和检查、团队共享记忆 review、个人记忆备份策略、立即备份和审计查询。
- Dockerfile 使用 Node 22 Dashboard build stage + Go build stage，最终镜像包含 `/usr/share/team-cloud-go/dashboard`。
- Kubernetes manifest 注入 `TEAM_CLOUD_DASHBOARD_ENABLED=true` 和 `TEAM_CLOUD_DASHBOARD_DIR=/usr/share/team-cloud-go/dashboard`。
- 新增 minikube 本地 Kubernetes 部署手册，覆盖 PostgreSQL/pgvector、SpiceDB、MinIO、Team Cloud Go + Dashboard 和本地 Hermes 连接。
