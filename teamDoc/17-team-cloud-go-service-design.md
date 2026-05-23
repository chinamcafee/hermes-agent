# 17. Team Cloud Go 服务端设计

日期：2026-05-23

## 1. 设计结论

Team Cloud 首次上线部署目标改为 Go 语言服务端，代码位于 `team_cloud_go/`。Python `team_cloud/` 保留为历史参考实现和测试资料来源，但不再作为云端生产部署目标。

Team Cloud 管理台随 Go 服务一体部署，代码位于 `team_cloud_go/dashboard/`。该管理台使用 React + Next.js static export，构建产物由 Go 服务在 `/dashboard/` 托管。Hermes 本地 dashboard/CLI 不承载团队云端管理职责，只负责本地个人事务、Hermes runtime 操作和 Team Cloud 远程地址/token 配置。

该决策基于以下原因：

- 团队协作需要独立云端服务，不能把成员管理、团队记忆同步和 review queue 都放在单个 `hermes-agent` 进程内。
- Go 单二进制和静态镜像更适合 Kubernetes 部署、滚动升级和多副本运行。
- Python `team_cloud/` 从未上线，不存在需要兼容的外部生产流量；首次上线可直接使用 Go API 和 Go schema。

## 2. 服务边界

Go Team Cloud 负责：

- 组织、团队、成员生命周期 API。
- Service token 鉴权、Casdoor 风格 RS256/JWKS JWT 校验、业务 API 授权、健康检查、readiness 和 Prometheus 文本指标。
- personal/team_shared 双层记忆 CRUD、embedding、prefetch、observation 和 review queue。
- 个人记忆备份策略 API。
- 个人备份 policy 调度、manual run、AES-GCM JSONL 对象上传、restore preview 和 restore execute。
- Audit event、授权 relationship/check、组织导出、删除请求、工具策略和 runtime event bridge。
- PostgreSQL 持久化 schema 和 repository。
- 容器镜像、Kubernetes Secret/Deployment/Service 部署资产。
- `/dashboard/` 静态管理台托管、首次初始化状态 API 和超级管理员 bootstrap API。

Go Team Cloud 不负责：

- Hermes Agent loop、工具执行和模型调用。
- Casdoor 登录页面或密码存储。
- SpiceDB 作为 ReBAC 引擎的内部实现。
- MinIO 对象存储内部实现。
- 本地 Hermes dashboard/CLI 的团队云端管理页面。

## 3. 代码结构

```text
team_cloud_go/
  cmd/team-cloud-server/main.go       # 服务入口，按环境变量选择后端
  internal/config/config.go           # 环境变量配置
  internal/httpapi/server.go          # HTTP 路由和 JSON API
  internal/store/store.go             # 后端接口
  internal/store/memory/store.go      # 开发和测试内存后端
  internal/store/postgres/schema.go   # PostgreSQL tcg_* schema
  internal/store/postgres/store.go    # 生产 PostgreSQL 后端
  internal/authn/authn.go              # RS256/JWKS JWT 校验
  internal/authz/authz.go              # local / SpiceDB HTTP 授权适配
  internal/backup/exporter.go          # AES-GCM JSONL personal backup exporter
  internal/objectstore/s3.go           # S3/MinIO path-style object store client
  dashboard/                           # Next.js static export 管理台
  deploy/kubernetes/team-cloud-go.yaml
  Dockerfile
```

## 3.1 Dashboard 和 Bootstrap

Dashboard 静态资源由以下配置控制：

- `TEAM_CLOUD_DASHBOARD_ENABLED=true`
- `TEAM_CLOUD_DASHBOARD_DIR=/usr/share/team-cloud-go/dashboard`

Go 服务注册：

- `GET /dashboard`：重定向到 `/dashboard/`。
- `GET /dashboard/*`：托管 Dashboard 静态资源，未知路径回退到 `index.html`。
- `GET /v1/bootstrap/status`：无 token 返回初始化状态、组件 readiness 和 owner 计数。
- `POST /v1/bootstrap/super-admin`：只接受 service token，创建组织、owner 成员和 `organization#owner` relationship；已经初始化后返回 `409 already_initialized`。

Dashboard 页面覆盖：

- 首次初始化和超级管理员创建。
- 组织、团队、成员邀请和成员查询。
- 授权 relationship 写入和 permission check。
- 团队共享记忆 review approve/reject。
- 个人记忆备份 policy、立即备份和调度参数。
- 审计事件查询。
- 本地 Hermes dashboard/CLI 连接 Team Cloud 的远程地址和 token 配置确认。

## 4. 数据模型

Go 版生产后端使用 `tcg_*` 表，采用稳定文本 ID：

- `tcg_organizations`
- `tcg_teams`
- `tcg_members`
- `tcg_memory_items`
- `tcg_memory_review_items`
- `tcg_memory_observations`
- `tcg_backup_policies`
- `tcg_audit_events`
- `tcg_relationships`
- `tcg_backup_jobs`
- `tcg_restore_previews`
- `tcg_org_exports`
- `tcg_deletion_requests`
- `tcg_tool_policy_rules`
- `tcg_cloud_sessions`
- `tcg_runtime_events`

文本 ID 与 HTTP API 保持一致，例如：

- `org_id = hermes-labs`
- `team_id = hermes-labs:platform`
- `member_id = hermes-labs:alice`

由于 Python 版未上线，Go 版不提供从 Python schema 到 Go schema 的线上兼容迁移。首次上线直接初始化 Go schema。

## 5. 双层记忆序列

`/v1/memory/prefetch` 返回 `partitions`：

- `personal`：按 `org_id + subject_member_id` 过滤，只在 `include_personal=true` 时返回。
- `team_shared`：按 `org_id + team_id + project_id` 过滤，只返回 `active` 记忆；JWT 请求会对每条团队记忆执行 `read_team` 授权检查。

`team_shared` 记忆默认进入 `pending_review`，只有 review approve 后才变为 `active` 并参与召回。

Go 版 `tcg_memory_items` 包含 `embedding vector(1536)`。写入 memory 时可传入 1536 维 `embedding`，prefetch 时可传入 1536 维 `query_embedding`；PostgreSQL 后端在有 query embedding 时使用 pgvector SQL `embedding <=> $vector` 排序并走 HNSW 索引路径，内存后端使用同一 cosine 排序语义。召回后再按 JWT principal 执行 `read_team` 过滤。生产 PostgreSQL 必须安装 pgvector extension。

## 6. 部署和运行

生产环境必须设置：

- `TEAM_CLOUD_SERVICE_TOKEN`
- `TEAM_CLOUD_DATABASE_URL`
- `TEAM_CLOUD_AUTO_MIGRATE=true`
- `TEAM_CLOUD_CASDOOR_ISSUER`
- `TEAM_CLOUD_CASDOOR_AUDIENCE`
- `TEAM_CLOUD_CASDOOR_JWKS_URL`
- `TEAM_CLOUD_AUTHZ_MODE=spicedb_http`
- `TEAM_CLOUD_AUTHZ_ENDPOINT`
- `TEAM_CLOUD_AUTHZ_TOKEN`
- `TEAM_CLOUD_BACKUP_OBJECT_MODE=s3`
- `TEAM_CLOUD_BACKUP_S3_ENDPOINT`
- `TEAM_CLOUD_BACKUP_S3_BUCKET`
- `TEAM_CLOUD_BACKUP_S3_ACCESS_KEY_ID`
- `TEAM_CLOUD_BACKUP_S3_SECRET_ACCESS_KEY`
- `TEAM_CLOUD_BACKUP_ENCRYPTION_KEY`
- `TEAM_CLOUD_BACKUP_SCHEDULER_ENABLED=true`
- `TEAM_CLOUD_BACKUP_SCHEDULER_INTERVAL_SECONDS=3600`
- `TEAM_CLOUD_DASHBOARD_ENABLED=true`
- `TEAM_CLOUD_DASHBOARD_DIR=/usr/share/team-cloud-go/dashboard`

开发环境可以不设置 `TEAM_CLOUD_DATABASE_URL`，此时使用内存后端；该模式不适合多成员协作和 Kubernetes 多副本。

Kubernetes 部署入口：

```bash
cd team_cloud_go
docker build -t ghcr.io/hermes-agent/team-cloud-go:0.1.0 .
kubectl apply -f deploy/kubernetes/team-cloud-go.yaml
```

镜像构建使用 Node 22 Alpine 阶段执行 `team_cloud_go/dashboard` 的 `npm ci` 和 `npm run build`，最终 distroless 镜像只复制 Go 二进制和 Dashboard `out/` 静态产物。

## 7. 验证

Go 服务端当前最小 GA 验证命令：

```bash
cd team_cloud_go
go test ./...
go vet ./...
```

验证覆盖：

- 服务 token 保护。
- Dashboard 静态托管、SPA fallback 和禁用开关。
- bootstrap status、super-admin 创建、owner relationship 和重复初始化冲突。
- Casdoor 风格 RS256/JWKS JWT 校验。
- JWT org/member scope 防伪造和高风险业务入口授权。
- SpiceDB/Authzed compatible HTTP relationship write、permission check 和 readiness fail-closed。
- 组织、团队、成员生命周期。
- personal/team_shared 双层记忆召回、`query_embedding` 语义排序和 `read_team` 过滤。
- team_shared review approve。
- 个人记忆备份策略。
- enabled backup policy 调度、cadence 到期判断、retention_count 修剪、个人备份 run、AES-GCM JSONL 对象上传、restore preview 和 restore execute。
- restore preview/execute 在对象模式下读取 S3/MinIO 加密对象，校验 checksum，解密 JSONL 后刷新恢复快照；restore execute 必须先完成 restore preview。
- restore mode 覆盖 `merge`、`overwrite` 和 `archive_current_then_restore`。
- 高风险治理 API 覆盖 authz relationship、audit、review、backup detail、deletion execute、runtime event 和 org list 的 JWT 业务授权负测。
- 审计事件、授权 relationship/check、组织导出、删除请求、工具策略和 runtime event。
- PostgreSQL schema 关键表。
- Dockerfile 和 Kubernetes manifest 必备部署约束。
- Next.js Dashboard `npm test -- --run`、`npm run type-check` 和 `npm run build`。

## 8. SpiceDB/Authzed 和 MinIO 接入状态

Go 服务端已实现两种授权模式：

- `local`：开发和单元测试使用 PostgreSQL/local relationship。
- `spicedb_http`：生产使用远程 SpiceDB/Authzed compatible HTTP API，支持 relationship write、permission check 和 readiness fail-closed。

未引入 `authzed-go` gRPC SDK，原因是评估版本链会提升到 Go 1.25 并破坏 Go 1.24 镜像基线。当前实现采用 Go 标准库 HTTP adapter，避免授权 SDK 反向牵引服务端基础运行时。

个人备份支持两种对象模式：

- `database`：开发默认模式，只保留数据库 snapshot。
- `s3`/`minio`：生产模式，生成 AES-256-GCM 加密 JSONL，通过 S3 Signature V4 path-style PUT 上传到 MinIO/S3，并写回 backup job manifest。

服务端启动后会在 `TEAM_CLOUD_BACKUP_SCHEDULER_ENABLED=true` 时启动轻量调度器，按 `TEAM_CLOUD_BACKUP_SCHEDULER_INTERVAL_SECONDS` 扫描 enabled personal backup policy。调度器只执行 `next_run_at` 已到期或尚未运行过的 policy，成功后写入 `last_run_at`/`next_run_at`，并按 `retention_count` 将旧 backup job 标记为 `pruned`。
