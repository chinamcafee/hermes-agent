# Hermes Team Cloud Service

`team_cloud` 是 Team Cloud 服务端的 Go 语言实现。该目录是独立 Go module，默认启动即注册团队管理、Casdoor 风格 JWT 鉴权、业务 API 授权、团队记忆、团队父人格、review queue、团队记忆备份恢复、审计、授权关系检查、组织导出、删除请求、工具策略 API 和 `/dashboard/` 管理台。

Dashboard 位于 `team_cloud/dashboard/`，使用 React + Next.js static export 构建，随 Go 服务镜像一起部署。未初始化时只显示独立初始化引导页；初始化完成后使用超级管理员或管理员帐号密码登录后台。第一版 Dashboard 只暴露单团队管理模型，团队成员、权限、记忆治理、团队父人格、团队备份和审计都属于该服务端管理台；本地 Hermes dashboard/CLI 只负责本地个人事务和远程 Team Cloud 地址/token 配置。

## 本地运行

开发内存后端：

```bash
cd team_cloud
go run ./cmd/team-cloud-server
```

PostgreSQL 后端：

```bash
cd team_cloud
TEAM_CLOUD_DATABASE_URL='postgres://hermes:secret@localhost:5432/hermes_team_cloud?sslmode=disable' \
TEAM_CLOUD_REDIS_ADDR='localhost:6379' \
TEAM_CLOUD_AUTO_MIGRATE=true \
go run ./cmd/team-cloud-server
```

## 环境变量

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `TEAM_CLOUD_SERVICE_NAME` | `team-cloud-go` | 健康检查和日志中的服务名。 |
| `TEAM_CLOUD_VERSION` | `0.1.0` | 健康检查版本号。 |
| `TEAM_CLOUD_BIND_ADDR` | `:8780` | HTTP 监听地址。 |
| `TEAM_CLOUD_DATABASE_URL` | 空 | 为空时使用内存后端；生产环境必须设置 PostgreSQL DSN。 |
| `TEAM_CLOUD_REDIS_ADDR` | 空 | Dashboard 登录 session token 的 Redis 地址；为空时仅用于开发/测试的进程内 session store。 |
| `TEAM_CLOUD_REDIS_PASSWORD` | 空 | Redis 密码。 |
| `TEAM_CLOUD_REDIS_DB` | `0` | Redis DB index。 |
| `TEAM_CLOUD_SESSION_TTL_SECONDS` | `43200` | Dashboard 用户登录 token 有效期，默认 12 小时。 |
| `TEAM_CLOUD_AUTO_MIGRATE` | `true` | 启动时自动执行 Go 服务 schema。 |
| `TEAM_CLOUD_CASDOOR_ISSUER` | 空 | Casdoor JWT `iss`。 |
| `TEAM_CLOUD_CASDOOR_AUDIENCE` | 空 | Casdoor JWT `aud`。 |
| `TEAM_CLOUD_CASDOOR_JWKS_URL` | 空 | Casdoor JWKS URL，用于 RS256 token 校验。 |
| `TEAM_CLOUD_AUTHZ_MODE` | `local` | `local` 使用 PostgreSQL/local relationship；`spicedb_http` 使用远程 SpiceDB/Authzed compatible HTTP API。 |
| `TEAM_CLOUD_AUTHZ_ENDPOINT` | 空 | `spicedb_http` 模式的远程授权端点，例如 `http://spicedb:8443`。 |
| `TEAM_CLOUD_AUTHZ_TOKEN` | 空 | 远程授权 API Bearer token。 |
| `TEAM_CLOUD_BACKUP_OBJECT_MODE` | `database` | `database` 仅使用 DB snapshot；`s3`/`minio` 上传团队记忆加密 JSONL 和团队父人格 JSON manifest 到对象存储。 |
| `TEAM_CLOUD_BACKUP_S3_ENDPOINT` | 空 | S3/MinIO endpoint，例如 `http://minio:9000`。 |
| `TEAM_CLOUD_BACKUP_S3_BUCKET` | 空 | 团队级备份 bucket，团队记忆和团队父人格用不同 object key prefix 区分。 |
| `TEAM_CLOUD_BACKUP_S3_REGION` | `us-east-1` | S3 signing region。 |
| `TEAM_CLOUD_BACKUP_S3_ACCESS_KEY_ID` | 空 | S3/MinIO access key。 |
| `TEAM_CLOUD_BACKUP_S3_SECRET_ACCESS_KEY` | 空 | S3/MinIO secret key。 |
| `TEAM_CLOUD_BACKUP_ENCRYPTION_KEY` | 空 | 团队记忆备份 AES-GCM 加密密钥材料；对象存储模式必须由 Secret 注入。团队父人格备份使用 JSON manifest snapshot。 |
| `TEAM_CLOUD_BACKUP_SCHEDULER_ENABLED` | `true` | 是否启动服务端 enabled backup policy 调度器。 |
| `TEAM_CLOUD_BACKUP_SCHEDULER_INTERVAL_SECONDS` | `3600` | 备份调度器扫描 enabled policy 的间隔。 |
| `TEAM_CLOUD_DASHBOARD_ENABLED` | `true` | 是否注册 `/dashboard/` 静态管理台路由。 |
| `TEAM_CLOUD_DASHBOARD_DIR` | `dashboard/out` | Dashboard static export 目录；容器内为 `/usr/share/team-cloud-go/dashboard`。 |

## API 概览

健康检查：

- `GET /healthz`
- `GET /readyz`
- `GET /metrics`
- `GET /dashboard/`

首次初始化：

- `GET /v1/bootstrap/status`
- `POST /v1/bootstrap/super-admin`
- `POST /v1/auth/login`

团队空间和成员：

- `POST /api/organizations`
- `GET /api/organizations`
- `POST /api/organizations/{org_id}/members`
- `POST /api/organizations/{org_id}/members/invite`
- `GET /api/organizations/{org_id}/members`
- `PATCH /api/organizations/{org_id}/members/{member_id}`
- `PATCH /api/organizations/{org_id}/members/{member_id}/disable`

团队记忆：

- `POST /v1/memory`
- `GET /v1/memory`
- `PATCH /v1/memory/{id}`
- `DELETE /v1/memory/{id}`
- `POST /v1/memory/{id}/archive`
- `POST /v1/memory/{id}/disable`
- `POST /v1/memory/{id}/restore`
- `POST /v1/memory/prefetch`
- `POST /v1/memory/observations`
- `GET /v1/memory/review`
- `POST /v1/memory/review/{review_id}/approve`
- `POST /v1/memory/review/{review_id}/reject`
- `GET /v1/team-memory-backup-policy`
- `PUT /v1/team-memory-backup-policy`
- `GET /v1/team-soul-backup-policy`
- `PUT /v1/team-soul-backup-policy`

团队父人格：

- `GET /v1/team-soul`
- `PUT /v1/team-soul`
- `GET /v1/runtime/team-soul`

治理、备份和运行时：

- `GET /v1/audit/events`
- `PUT /v1/authz/relationships`
- `POST /v1/authz/check`
- `POST /v1/backups/team/run`
- `GET /v1/backups/team`
- `GET /v1/backups/team/{backup_id}`
- `POST /v1/backups/team/{backup_id}/restore-preview`
- `POST /v1/backups/team/{backup_id}/restore-execute`
- `POST /v1/backups/team-soul/run`
- `GET /v1/backups/team-soul`
- `POST /v1/backups/team-soul/{backup_id}/restore-preview`
- `POST /v1/backups/team-soul/{backup_id}/restore-execute`
- `POST /v1/exports/org`
- `POST /v1/deletion-requests`
- `POST /v1/deletion-requests/{request_id}/execute`
- `PUT /v1/tool-policy/rules`
- `POST /v1/tool-policy/evaluate`
- `POST /v1/sessions`
- `POST /v1/runtime/events`

鉴权支持：

- 首次初始化：`POST /v1/bootstrap/super-admin` 不需要预置 token，只在尚未初始化时允许调用。
- Dashboard session token：`POST /v1/auth/login` 使用 `super_admin` 或 `admin` 帐号密码登录后返回 `hcs_...` opaque token；服务端把 token 摘要和 principal 写入 Redis，并在后续 API 中按 Bearer token 鉴权。
- Casdoor 风格 RS256 JWT：配置 `TEAM_CLOUD_CASDOOR_ISSUER`、`TEAM_CLOUD_CASDOOR_AUDIENCE`、`TEAM_CLOUD_CASDOOR_JWKS_URL` 后，Bearer token 会按 JWKS 校验签名、issuer、audience 和 expiration。
- 授权：JWT 请求会校验 `hermes_org_id`、`hermes_member_id` 与请求 payload/query 的 org/member scope；组织、成员、团队记忆、团队父人格、备份、导出、工具策略和 runtime API 走 relationship/check fail-closed。第一版没有独立工作组资源，团队级权限统一落在 `organization:{org_id}`。生产可设置 `TEAM_CLOUD_AUTHZ_MODE=spicedb_http` 接入远程 SpiceDB/Authzed compatible HTTP API。
- 团队记忆：Team Cloud 只接受 `scope=team_shared`。`scope=personal` 已退役，个人记忆只保存在成员本地 Hermes profile，并由 `/cloud-backup memory` 自行备份。`team_shared` prefetch 会对每条 team memory 执行 `organization:{org_id}#read_team` 检查，无授权时过滤该团队分区。Dashboard 管理台支持按 `source_type=auto_extracted/admin_created` 展示来源标签、管理员创建团队记忆、编辑内容、停用为 `archived` 和硬删除。
- 团队父人格：Dashboard 管理团队父人格正文、版本、checksum 和审计；Hermes CLI/Desktop 只能通过 Agent Bridge 读取，不能直接写团队父人格。
- 向量检索：`POST /v1/memory` 可写入 `embedding` 数组，`POST /v1/memory/prefetch` 可传入 `query_embedding` 数组；PostgreSQL 后端使用 pgvector `embedding vector(1536)`、HNSW cosine index 和 `embedding <=> $vector` SQL 排序，内存后端使用同一 cosine 排序语义。
- 团队备份：`POST /v1/backups/team/run` 备份团队记忆，`POST /v1/backups/team-soul/run` 备份团队父人格。`TEAM_CLOUD_BACKUP_OBJECT_MODE=s3` 时，团队记忆生成 AES-256-GCM 加密 JSONL，团队父人格生成 JSON manifest，二者上传到 S3/MinIO path-style bucket，并在 backup job manifest 中登记 checksum、bucket 和 object key。restore execute 必须先调用 restore preview；团队记忆恢复按 memory id upsert，团队父人格恢复按 `org_id + team_id` upsert。

## Kubernetes 部署

```bash
cd team_cloud
docker build -t ghcr.io/hermes-agent/team-cloud-go:0.1.0 .
kubectl apply -f deploy/kubernetes/team-cloud-go.yaml
```

生产环境必须把 `team-cloud-go.yaml` 中的 `TEAM_CLOUD_DATABASE_URL`、`TEAM_CLOUD_REDIS_PASSWORD` 和 `TEAM_CLOUD_AUTHZ_TOKEN` 替换为集群内 Secret 管理系统生成的值。只有启用 `TEAM_CLOUD_BACKUP_OBJECT_MODE=s3` 时，才需要提供 `TEAM_CLOUD_BACKUP_S3_*` 和 `TEAM_CLOUD_BACKUP_ENCRYPTION_KEY`。部署后访问 `http://<host>:8780/dashboard/`，初始化向导只创建团队和唯一超级管理员；PostgreSQL、Redis 等连接配置由 Kubernetes Secret / env 注入，MinIO/S3 是团队记忆和团队父人格备份的可选对象存储。

## 验证

```bash
cd team_cloud
go test ./...
go vet ./...

cd dashboard
npm test -- --run
npm run type-check
npm run build
```
