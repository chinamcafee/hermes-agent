# Hermes Team Cloud Go Service

`team_cloud_go` 是 Team Cloud 服务端的 Go 语言实现，用于替代未上线的 Python `team_cloud/` 服务。该目录是独立 Go module，默认启动即注册团队管理、Casdoor 风格 JWT 鉴权、业务 API 授权、双层记忆、review queue、个人记忆加密备份恢复、审计、授权关系检查、组织导出、删除请求、工具策略 API 和 `/dashboard/` 管理台。

Dashboard 位于 `team_cloud_go/dashboard/`，使用 React + Next.js static export 构建，随 Go 服务镜像一起部署。首次初始化、超级管理员创建、组织/团队/成员、权限、记忆治理、备份和审计管理都属于该服务端管理台；本地 Hermes dashboard/CLI 只负责本地个人事务和远程 Team Cloud 地址/token 配置。

## 本地运行

开发内存后端：

```bash
cd team_cloud_go
TEAM_CLOUD_SERVICE_TOKEN=dev-token go run ./cmd/team-cloud-server
```

PostgreSQL 后端：

```bash
cd team_cloud_go
TEAM_CLOUD_SERVICE_TOKEN=dev-token \
TEAM_CLOUD_DATABASE_URL='postgres://hermes:secret@localhost:5432/hermes_team_cloud?sslmode=disable' \
TEAM_CLOUD_AUTO_MIGRATE=true \
go run ./cmd/team-cloud-server
```

## 环境变量

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `TEAM_CLOUD_SERVICE_NAME` | `team-cloud-go` | 健康检查和日志中的服务名。 |
| `TEAM_CLOUD_VERSION` | `0.1.0` | 健康检查版本号。 |
| `TEAM_CLOUD_BIND_ADDR` | `:8780` | HTTP 监听地址。 |
| `TEAM_CLOUD_SERVICE_TOKEN` | 空 | 为空时关闭服务 token 鉴权；生产环境必须设置。 |
| `TEAM_CLOUD_DATABASE_URL` | 空 | 为空时使用内存后端；生产环境必须设置 PostgreSQL DSN。 |
| `TEAM_CLOUD_AUTO_MIGRATE` | `true` | 启动时自动执行 Go 服务 schema。 |
| `TEAM_CLOUD_CASDOOR_ISSUER` | 空 | Casdoor JWT `iss`。为空时只接受 service token。 |
| `TEAM_CLOUD_CASDOOR_AUDIENCE` | 空 | Casdoor JWT `aud`。 |
| `TEAM_CLOUD_CASDOOR_JWKS_URL` | 空 | Casdoor JWKS URL，用于 RS256 token 校验。 |
| `TEAM_CLOUD_AUTHZ_MODE` | `local` | `local` 使用 PostgreSQL/local relationship；`spicedb_http` 使用远程 SpiceDB/Authzed compatible HTTP API。 |
| `TEAM_CLOUD_AUTHZ_ENDPOINT` | 空 | `spicedb_http` 模式的远程授权端点，例如 `http://spicedb:8443`。 |
| `TEAM_CLOUD_AUTHZ_TOKEN` | 空 | 远程授权 API Bearer token。 |
| `TEAM_CLOUD_BACKUP_OBJECT_MODE` | `database` | `database` 仅使用 DB snapshot；`s3`/`minio` 上传加密 JSONL 到对象存储。 |
| `TEAM_CLOUD_BACKUP_S3_ENDPOINT` | 空 | S3/MinIO endpoint，例如 `http://minio:9000`。 |
| `TEAM_CLOUD_BACKUP_S3_BUCKET` | 空 | 个人备份 bucket。 |
| `TEAM_CLOUD_BACKUP_S3_REGION` | `us-east-1` | S3 signing region。 |
| `TEAM_CLOUD_BACKUP_S3_ACCESS_KEY_ID` | 空 | S3/MinIO access key。 |
| `TEAM_CLOUD_BACKUP_S3_SECRET_ACCESS_KEY` | 空 | S3/MinIO secret key。 |
| `TEAM_CLOUD_BACKUP_ENCRYPTION_KEY` | 空 | 个人备份 AES-GCM 加密密钥材料；生产环境必须由 Secret 注入。 |
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

组织、团队和成员：

- `POST /api/organizations`
- `GET /api/organizations`
- `POST /api/organizations/{org_id}/teams`
- `GET /api/organizations/{org_id}/teams`
- `POST /api/organizations/{org_id}/members/invite`
- `GET /api/organizations/{org_id}/members`
- `PATCH /api/organizations/{org_id}/members/{member_id}/disable`

双层记忆：

- `POST /v1/memory`
- `GET /v1/memory`
- `PATCH /v1/memory/{id}`
- `DELETE /v1/memory/{id}`
- `POST /v1/memory/{id}/archive`
- `POST /v1/memory/{id}/restore`
- `POST /v1/memory/prefetch`
- `POST /v1/memory/observations`
- `GET /v1/memory/review`
- `POST /v1/memory/review/{review_id}/approve`
- `POST /v1/memory/review/{review_id}/reject`
- `GET /v1/me/memory-backup-policy`
- `PUT /v1/me/memory-backup-policy`

治理、备份和运行时：

- `GET /v1/audit/events`
- `PUT /v1/authz/relationships`
- `POST /v1/authz/check`
- `POST /v1/backups/personal/run`
- `GET /v1/backups/personal/{backup_id}`
- `POST /v1/backups/personal/{backup_id}/restore-preview`
- `POST /v1/backups/personal/{backup_id}/restore-execute`
- `POST /v1/exports/org`
- `POST /v1/deletion-requests`
- `POST /v1/deletion-requests/{request_id}/execute`
- `PUT /v1/tool-policy/rules`
- `POST /v1/tool-policy/evaluate`
- `POST /v1/sessions`
- `POST /v1/runtime/events`

鉴权支持：

- service token：`Authorization: Bearer <token>` 或 `X-Hermes-Team-Cloud-Token: <token>`。
- Casdoor 风格 RS256 JWT：配置 `TEAM_CLOUD_CASDOOR_ISSUER`、`TEAM_CLOUD_CASDOOR_AUDIENCE`、`TEAM_CLOUD_CASDOOR_JWKS_URL` 后，Bearer token 会按 JWKS 校验签名、issuer、audience 和 expiration。
- 授权：JWT 请求会校验 `hermes_org_id`、`hermes_member_id` 与请求 payload/query 的 org/member scope；组织、成员、团队记忆、备份、导出、删除、工具策略和 runtime API 走 relationship/check fail-closed。生产可设置 `TEAM_CLOUD_AUTHZ_MODE=spicedb_http` 接入远程 SpiceDB/Authzed compatible HTTP API。
- 团队记忆：`team_shared` prefetch 会对每条 team memory 执行 `read_team` 检查，无授权时过滤该团队分区。
- 向量检索：`POST /v1/memory` 可写入 `embedding` 数组，`POST /v1/memory/prefetch` 可传入 `query_embedding` 数组；PostgreSQL 后端使用 pgvector `embedding vector(1536)`、HNSW cosine index 和 `embedding <=> $vector` SQL 排序，内存后端使用同一 cosine 排序语义。
- 个人备份：`TEAM_CLOUD_BACKUP_OBJECT_MODE=s3` 时，`POST /v1/backups/personal/run` 会生成 AES-256-GCM 加密 JSONL，上传到 S3/MinIO path-style bucket，并在 backup job manifest 中登记 checksum、bucket、object key 和加密格式。restore preview/execute 会读取对象、校验 checksum 并解密 JSONL。服务端调度器会按 `TEAM_CLOUD_BACKUP_SCHEDULER_INTERVAL_SECONDS` 扫描 enabled backup policy，并尊重 cadence/retention_count。`restore-execute` 必须先调用 `restore-preview`，支持 `merge`、`overwrite` 和 `archive_current_then_restore`。

## Kubernetes 部署

```bash
cd team_cloud_go
docker build -t ghcr.io/hermes-agent/team-cloud-go:0.1.0 .
kubectl apply -f deploy/kubernetes/team-cloud-go.yaml
```

生产环境必须把 `team-cloud-go.yaml` 中的 `TEAM_CLOUD_SERVICE_TOKEN`、`TEAM_CLOUD_DATABASE_URL`、`TEAM_CLOUD_AUTHZ_TOKEN`、`TEAM_CLOUD_BACKUP_S3_*` 和 `TEAM_CLOUD_BACKUP_ENCRYPTION_KEY` 替换为集群内 Secret 管理系统生成的值。部署后访问 `http://<host>:8780/dashboard/`，使用 service token 完成首次初始化。

## 验证

```bash
cd team_cloud_go
go test ./...
go vet ./...

cd dashboard
npm test -- --run
npm run type-check
npm run build
```
