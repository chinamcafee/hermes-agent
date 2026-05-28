# 17. Team Cloud 服务端设计

日期：2026-05-23

## 1. 设计结论

Team Cloud 首次上线部署目标为 Go 语言服务端，代码位于 `team_cloud/`。旧 Python 服务端已经删除，不再作为参考实现、测试资料来源或云端生产部署目标。

Team Cloud 管理台随 Go 服务一体部署，代码位于 `team_cloud/dashboard/`。该管理台使用 React + Next.js static export，构建产物由 Go 服务在 `/dashboard/` 托管。Hermes 本地 dashboard/CLI/Desktop 不承载团队云端管理职责，只负责本地个人事务、Hermes runtime 操作和 Team Cloud 远程地址/token 配置。

该决策基于以下原因：

- 团队协作需要独立云端服务，不能把成员管理、团队记忆同步和 review queue 都放在单个 `hermes-agent` 进程内。
- Go 单二进制和静态镜像更适合 Kubernetes 部署、滚动升级和多副本运行。
- 旧 Python 服务端从未上线，不存在需要兼容的外部生产流量；首次上线直接使用 Go API 和 Go schema。

## 2. 服务边界

Team Cloud Go 服务负责：

- 组织、团队、成员生命周期 API。
- Dashboard 用户级 session token、Redis session store、Casdoor 风格 RS256/JWKS JWT 校验、业务 API 授权、健康检查、readiness 和 Prometheus 文本指标。
- team_shared 团队记忆 CRUD、embedding、prefetch、observation 和 review queue。
- 团队父人格 CRUD、版本、审计、runtime 只读 API 和 Dashboard 人格治理。
- 团队记忆和团队父人格备份策略 API。
- 团队记忆和团队父人格备份 policy 调度、manual run、backup history、restore preview 和 restore execute。团队记忆对象使用 AES-GCM JSONL；团队父人格对象使用包含 `team_soul` snapshot 的 JSON manifest。
- Audit event、授权 relationship/check、组织导出、工具策略和 runtime event bridge；个人记忆删除请求不属于 Team Cloud Go 边界。
- PostgreSQL 持久化 schema 和 repository。
- 容器镜像、Kubernetes Secret/Deployment/Service 部署资产。
- `/dashboard/` 静态管理台托管、首次初始化状态 API 和超级管理员 bootstrap API。

Team Cloud Go 服务不负责：

- Hermes Agent loop、工具执行和模型调用。
- Casdoor 登录页面或密码存储。
- SpiceDB 作为 ReBAC 引擎的内部实现。
- MinIO 对象存储内部实现。
- 成员个人记忆、本地人格的云端管理和云端备份；个人记忆与本地 `SOUL.md` 保留在 Hermes 本地 profile，由 CLI `/cloud-backup memory|soul` 上传到用户指定对象存储。
- 本地 Hermes dashboard/CLI/Desktop 的团队云端管理页面。

## 3. 代码结构

```text
team_cloud/
  cmd/team-cloud-server/main.go       # 服务入口，按环境变量选择后端
  internal/config/config.go           # 环境变量配置
  internal/httpapi/server.go          # HTTP 路由和 JSON API
  internal/store/store.go             # 后端接口
  internal/store/memory/store.go      # 开发和测试内存后端
  internal/store/postgres/schema.go   # PostgreSQL tcg_* schema
  internal/store/postgres/store.go    # 生产 PostgreSQL 后端
  internal/authn/authn.go              # Dashboard session 和 RS256/JWKS JWT 校验
  internal/authn/session_store.go      # Redis / memory session token store
  internal/authz/authz.go              # local / SpiceDB HTTP 授权适配
  internal/backup/exporter.go          # AES-GCM JSONL memory backup exporter
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
- `GET /v1/bootstrap/status`：无 token 返回初始化状态、组件 readiness、PostgreSQL/Redis/可选对象存储配置检查、团队空间计数和超级管理员计数。
- `POST /v1/bootstrap/super-admin`：首次初始化开放调用，只创建一个团队空间和唯一 `super_admin` 成员，写入 `organization#owner` relationship；已经初始化后返回 `409 already_initialized`。
- `POST /v1/auth/login`：使用 `super_admin` 或 `admin` 帐号密码换取 Dashboard opaque session token，服务端把 token 摘要与 principal 写入 Redis。

Dashboard 页面覆盖：

- 独立首次初始化引导页，不与后台导航 Tab 同层级。
- PostgreSQL、Redis 和可选对象存储健康状态。
- Step-by-Step 团队和唯一超级管理员初始化。
- 后台帐号密码登录。
- 单团队成员列表、直接创建管理员或用户、成员查询和停用。
- 权限中心只读角色矩阵和服务端固定权限说明。
- 团队共享记忆 review approve/reject。
- 团队记忆备份管理、备份历史、立即备份、策略设置和恢复。
- 团队父人格治理、版本查看、恢复和团队父人格备份管理。
- 审计事件查询。
- 本地 Hermes dashboard/CLI/Desktop 连接 Team Cloud 的远程地址和 token 配置确认。

Hermes Desktop 只应通过 Hermes Agent Runtime Bridge 接入 Team Cloud。Desktop 可以打开 `/dashboard/`，但不直接调用 Team Cloud `/v1/auth/login`、`/v1/memory`、成员管理或备份恢复 API 作为主路径。

## 4. 数据模型

Go 版生产后端使用 `tcg_*` 表，采用稳定文本 ID：

- `tcg_organizations`
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
- `tcg_team_souls`

文本 ID 与 HTTP API 保持一致，例如：

- `org_id = hermes-labs`
- `team_id = hermes-labs:platform`
- `member_id = hermes-labs:alice`

旧 Python 服务端已经删除，当前版本不提供从 Python schema 到 Go schema 的线上兼容迁移。首次上线直接初始化 Go schema。

## 5. 记忆边界和团队记忆序列

`/v1/memory/prefetch` 返回 `partitions`：

- `team_shared`：按 `org_id + team_id + project_id` 过滤，只返回 `active` 记忆；JWT 请求会对每条团队记忆执行 `read_team` 授权检查。

Team Cloud 的 GA 主路径只管理团队记忆和团队父人格。个人记忆不进入 Team Cloud 管理台、不由 Dashboard 备份，也不通过 `TeamMemoryProvider` 从云端召回。Hermes CLI 继续使用本地 profile 记忆文件和本地 `SOUL.md`，并通过 `/cloud-backup memory|soul` 完成用户自主管理的 MinIO/S3-compatible 备份。

`team_shared` 记忆默认进入 `pending_review`，只有 review approve 后才变为 `active` 并参与召回。

CLI 显式新增团队记忆走 `team_memory_add`，直接写入 `status=active`。`/v1/memory/observations` 只保存可供后续抽取的 observation；Go 首发服务端当前不内置常驻 extraction worker，因此普通对话不会仅凭 observation 自动生成 Dashboard 可见记忆。

Dashboard 记忆治理对 `team_shared` 增加来源字段：

- `source_type=auto_extracted`：由成员客户端从个人记忆或会话 observation 中抽取，使用 `source_member_id` 标记来源成员。
- `source_type=admin_created`：由超级管理员或管理员在 Dashboard 中创建，使用 `created_by_member_id` 标记创建者。

管理员可以通过 Dashboard 编辑任意团队记忆内容、类型和敏感度；停用记忆写入 `status=archived`，不删除数据；`DELETE /v1/memory/{id}` 是硬删除，会移除该记忆及其 review 关联记录。

Go 版 `tcg_memory_items` 包含 `embedding vector(1536)`。写入 memory 时可传入 1536 维 `embedding`，prefetch 时可传入 1536 维 `query_embedding`；PostgreSQL 后端在有 query embedding 时使用 pgvector SQL `embedding <=> $vector` 排序并走 HNSW 索引路径，内存后端使用同一 cosine 排序语义。召回后再按 JWT principal 执行 `read_team` 过滤。生产 PostgreSQL 必须安装 pgvector extension。

## 5.1 团队父人格边界

2026-05-24 三方联动方案补充：Team Cloud 需要提供团队父人格管理。团队父人格是所有成员本地 `SOUL.md` 的父级约束；Hermes Agent 在 team mode 下同步该内容并与本地人格合成 effective soul，冲突时以团队父人格为准。

Team Cloud 负责：

- active team parent soul 的读取和编辑。
- 版本、checksum、审计和权限控制。
- Dashboard 人格治理页面。
- 团队父人格备份、历史和恢复；恢复前必须先执行 `restore-preview`，恢复时按 org/team active soul upsert 并递增版本。

Team Cloud 不负责成员本地 `SOUL.md` 的存储、编辑或本地人格备份。成员本地人格备份由 Hermes Agent `/cloud-backup soul ...` 写入用户配置的 MinIO/S3-compatible 对象存储。

2026-05-25 Dashboard 可见性补充：Team Cloud Dashboard 必须把团队父人格作为独立配置中心暴露，而不是隐藏在备份或概览信息中。当前管理台导航使用“团队父人格中心”，概览页提供配置中心提示，中心页负责：

- 显示管理态团队父人格正文、版本、checksum、更新时间和更新人。
- 显示 runtime API 当前读取到的团队父人格，用于核对 CLI/Desktop 实际会合并的父人格。
- 通过弹窗编辑并保存团队父人格。
- 将团队父人格备份和恢复入口保持在“备份管理”页，和团队记忆备份分区展示。

## 6. 部署和运行

生产环境必须设置：

- `TEAM_CLOUD_DATABASE_URL`
- `TEAM_CLOUD_REDIS_ADDR`
- `TEAM_CLOUD_REDIS_PASSWORD`
- `TEAM_CLOUD_SESSION_TTL_SECONDS`
- `TEAM_CLOUD_AUTO_MIGRATE=true`
- `TEAM_CLOUD_CASDOOR_ISSUER`
- `TEAM_CLOUD_CASDOOR_AUDIENCE`
- `TEAM_CLOUD_CASDOOR_JWKS_URL`
- `TEAM_CLOUD_AUTHZ_MODE=spicedb_http`
- `TEAM_CLOUD_AUTHZ_ENDPOINT`
- `TEAM_CLOUD_AUTHZ_TOKEN`
- `TEAM_CLOUD_BACKUP_SCHEDULER_ENABLED=true`
- `TEAM_CLOUD_BACKUP_SCHEDULER_INTERVAL_SECONDS=3600`
- `TEAM_CLOUD_DASHBOARD_ENABLED=true`
- `TEAM_CLOUD_DASHBOARD_DIR=/usr/share/team-cloud-go/dashboard`

团队级备份对象存储为可选项。需要把团队记忆或团队父人格备份对象上传到 S3/MinIO 时，再设置：

- `TEAM_CLOUD_BACKUP_OBJECT_MODE=s3`
- `TEAM_CLOUD_BACKUP_S3_ENDPOINT`
- `TEAM_CLOUD_BACKUP_S3_BUCKET`
- `TEAM_CLOUD_BACKUP_S3_ACCESS_KEY_ID`
- `TEAM_CLOUD_BACKUP_S3_SECRET_ACCESS_KEY`
- `TEAM_CLOUD_BACKUP_ENCRYPTION_KEY`

开发环境可以不设置 `TEAM_CLOUD_DATABASE_URL`，此时使用内存后端；该模式不适合多成员协作和 Kubernetes 多副本。

Kubernetes 部署入口：

```bash
cd team_cloud
docker build -t ghcr.io/hermes-agent/team-cloud-go:0.1.0 .
kubectl apply -f deploy/kubernetes/team-cloud-go.yaml
```

镜像构建使用 Node 22 Alpine 阶段执行 `team_cloud/dashboard` 的 `npm ci` 和 `npm run build`，最终 distroless 镜像只复制 Go 二进制和 Dashboard `out/` 静态产物。

## 7. 验证

Go 服务端当前最小 GA 验证命令：

```bash
cd team_cloud
go test ./...
go vet ./...
```

验证覆盖：

- Dashboard opaque session token 签发、Redis/memory session store 鉴权和缺失 token fail-closed。
- Dashboard 静态托管、SPA fallback 和禁用开关。
- bootstrap status、无 token super-admin 创建、owner relationship 和重复初始化冲突。
- Casdoor 风格 RS256/JWKS JWT 校验。
- JWT org/member scope 防伪造和高风险业务入口授权。
- SpiceDB/Authzed compatible HTTP relationship write、permission check 和 readiness fail-closed。
- 组织、团队、成员生命周期。
- team_shared 团队记忆召回、`query_embedding` 语义排序和 `read_team` 过滤。
- team_shared review approve。
- 团队记忆备份策略。
- enabled backup policy 调度、cadence 到期判断、retention_count 修剪、团队备份 run、AES-GCM JSONL 对象上传、restore preview 和 restore execute。
- restore preview/execute 在对象模式下读取 S3/MinIO 加密对象，校验 checksum，解密 JSONL 后刷新恢复快照；restore execute 必须先完成 restore preview；恢复按 memory id upsert，重复恢复不会新增重复记录。
- restore mode 当前 GA 主路径为 `merge`。
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

团队记忆和团队父人格备份支持两种对象模式：

- `database`：开发默认模式，只保留数据库 snapshot。
- `s3`/`minio`：生产模式。团队记忆生成 AES-256-GCM 加密 JSONL；团队父人格生成 JSON manifest，通过 S3 Signature V4 path-style PUT 上传到 MinIO/S3，并写回 backup job manifest。

服务端启动后会在 `TEAM_CLOUD_BACKUP_SCHEDULER_ENABLED=true` 时启动轻量调度器，按 `TEAM_CLOUD_BACKUP_SCHEDULER_INTERVAL_SECONDS` 扫描 enabled team memory 和 team soul backup policy。调度器只执行 `next_run_at` 已到期或尚未运行过的 policy，成功后写入 `last_run_at`/`next_run_at`，并按 `retention_count` 将旧 backup job 标记为 `pruned`。
