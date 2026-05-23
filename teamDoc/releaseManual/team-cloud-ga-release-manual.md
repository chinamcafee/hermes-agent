# Hermes Agent Team Cloud GA 使用手册

版本：Team Cloud GA
日期：2026-05-23
状态：GA

## 适用范围

本文档覆盖本轮新增的企业版团队功能开箱即用能力：

- 企业版团队功能开箱即用
- Casdoor 统一登录和身份同步
- SpiceDB 权限关系和 Permission Explorer
- PostgreSQL/pgvector 团队记忆存储与检索
- MinIO 备份对象和 manifest
- Team Cloud Go 服务端、Team API、`/dashboard/` 管理台、Web Chat、Gateway/API identity headers
- TeamMemoryProvider 个人记忆与团队共享记忆双层接入
- 本地记忆定时备份、恢复、组织导出、删除和保留策略
- 工具策略、高危审批、break-glass 和审计
- SessionDB 与 legacy memory provider 迁移
- Deployment smoke 和 GA 验证
- 运维、支持和 Post-GA backlog

本地 Kubernetes 全栈演练另见 [Team Cloud Go + Dashboard minikube 本地 Kubernetes 部署手册](team-cloud-go-minikube-dashboard-manual.md)。

## 企业版团队功能开箱即用

Team Cloud 的默认拓扑由以下组件组成：

| 组件 | 用途 | 关键验证 |
| --- | --- | --- |
| Casdoor | 组织登录、OIDC token、用户和组同步。 | `tests/team_cloud/test_casdoor_oidc.py`、`tests/team_cloud/test_casdoor_sync_worker.py` |
| SpiceDB | 组织、团队、项目、记忆、工具和备份权限关系。 | `tests/team_cloud/test_spicedb_client.py`、`tests/team_cloud/test_authz_middleware.py` |
| PostgreSQL/pgvector | Team Cloud 主库、memory schema、embedding 检索；Go 服务端使用 `embedding vector(1536)` 和 `query_embedding`。 | `tests/team_cloud/test_postgres_migrations.py`、`tests/team_cloud/test_memory_query_layer.py`、`team_cloud_go/internal/store/postgres/schema_test.go`、`team_cloud_go/internal/httpapi/server_test.go` |
| MinIO | 个人备份、组织导出和 restore staging 对象。 | `tests/team_cloud/test_minio_manifest.py`、`tests/team_cloud/test_backup_storage.py` |
| Team Cloud Go API | 组织/成员 API、memory API、review queue、个人备份策略 API、bootstrap API，首次上线默认服务端。 | `cd team_cloud_go && go test ./...`、`cd team_cloud_go && go vet ./...` |
| Team Cloud Go Dashboard | `/dashboard/` 静态管理台，覆盖首次初始化、超级管理员、组织团队成员、权限、记忆治理、备份和审计。 | `cd team_cloud_go/dashboard && npm test -- --run`、`npm run type-check`、`npm run build` |
| Gateway/API identity resolver | 消息平台和 API server 的团队身份注入。 | `tests/gateway/test_api_server_team_headers.py`、`tests/gateway/test_gateway_team_identity_resolver.py` |

默认上线顺序：

1. 构建并部署 `team_cloud_go/` Go 服务端和随镜像发布的 Dashboard。
2. 完成 Casdoor issuer、client、redirect URL 和 JWKS 配置。
3. 加载 SpiceDB schema，确认 pre-shared key 与 Team API secret 一致。
4. 执行 PostgreSQL migration，确认 pgvector extension 可用。
5. 初始化 MinIO bucket、manifest 和 lifecycle。
6. 打开 `/dashboard/`，使用 service token 通过 bootstrap 创建第一个 Owner。
7. 邀请管理员和成员。
8. 由 Owner 在 Dashboard 创建团队、成员和权限关系。
9. 运行 `cd team_cloud_go && go test ./...`、`go vet ./...`、`cd dashboard && npm test -- --run && npm run build` 留存 Go 服务端和 Dashboard 证据。
10. 运行 `scripts/team-cloud-foundation-smoke.sh` 留存 Hermes runtime 集成证据。

## 安装和首次登录

### Go 服务端 Kubernetes 部署

首次上线推荐部署 `team_cloud_go/`，不再部署 Python `team_cloud/` 作为 Team Cloud 服务端。

```bash
cd team_cloud_go
docker build -t ghcr.io/hermes-agent/team-cloud-go:0.1.0 .
kubectl apply -f deploy/kubernetes/team-cloud-go.yaml
kubectl rollout status deployment/hermes-team-cloud-go
```

Go 服务端镜像包含 `team_cloud_go/dashboard/` 的 Next.js static export。部署完成后：

```bash
kubectl port-forward svc/hermes-team-cloud-go 8780:8780
open http://localhost:8780/dashboard/
```

Dashboard 首次初始化调用：

- `GET /v1/bootstrap/status` 检查服务、后端、授权、对象存储和初始化状态。
- `POST /v1/bootstrap/super-admin` 使用 `TEAM_CLOUD_SERVICE_TOKEN` 创建第一个组织 Owner。
- 已经存在 Owner 后，bootstrap 会返回 `409 already_initialized`，后续管理员通过组织/成员页面扩展团队。

部署前必须替换 Kubernetes Secret：

- `TEAM_CLOUD_SERVICE_TOKEN`
- `TEAM_CLOUD_DATABASE_URL`
- `TEAM_CLOUD_DASHBOARD_ENABLED=true`
- `TEAM_CLOUD_DASHBOARD_DIR=/usr/share/team-cloud-go/dashboard`

生产环境要求：

- `TEAM_CLOUD_DATABASE_URL` 指向 PostgreSQL。
- `TEAM_CLOUD_AUTO_MIGRATE=true` 仅用于首发和受控升级；严格变更窗口可改为 `false` 并由迁移 Job 执行。
- `TEAM_CLOUD_SERVICE_TOKEN` 通过 Secret 管理，不写入镜像或 ConfigMap。
- `/readyz` 返回 `ready` 后再接入 Hermes runtime 和 Gateway。
- `/dashboard/` 能返回管理台 HTML，未知 Dashboard 子路径能回退到静态 `index.html`。

Go 服务端本地验证：

```bash
cd team_cloud_go
TEAM_CLOUD_SERVICE_TOKEN=dev-token \
TEAM_CLOUD_DATABASE_URL='postgres://hermes:secret@localhost:5432/hermes_team_cloud?sslmode=disable' \
go run ./cmd/team-cloud-server
```

Casdoor JWT 配置：

```bash
TEAM_CLOUD_CASDOOR_ISSUER=https://casdoor.example
TEAM_CLOUD_CASDOOR_AUDIENCE=hermes-team-cloud
TEAM_CLOUD_CASDOOR_JWKS_URL=https://casdoor.example/.well-known/jwks
```

配置后，Team Cloud Go 会按 JWKS 校验 RS256 Bearer token 的签名、issuer、audience 和 expiration。内部 automation 仍可使用 `TEAM_CLOUD_SERVICE_TOKEN`。

远程授权和个人备份对象配置：

```bash
TEAM_CLOUD_AUTHZ_MODE=spicedb_http
TEAM_CLOUD_AUTHZ_ENDPOINT=http://spicedb:8443
TEAM_CLOUD_AUTHZ_TOKEN=change-me

TEAM_CLOUD_BACKUP_OBJECT_MODE=s3
TEAM_CLOUD_BACKUP_S3_ENDPOINT=http://minio:9000
TEAM_CLOUD_BACKUP_S3_BUCKET=hermes-personal-backups
TEAM_CLOUD_BACKUP_S3_REGION=us-east-1
TEAM_CLOUD_BACKUP_S3_ACCESS_KEY_ID=change-me
TEAM_CLOUD_BACKUP_S3_SECRET_ACCESS_KEY=change-me
TEAM_CLOUD_BACKUP_ENCRYPTION_KEY=change-me
TEAM_CLOUD_BACKUP_SCHEDULER_ENABLED=true
TEAM_CLOUD_BACKUP_SCHEDULER_INTERVAL_SECONDS=3600
```

`spicedb_http` 和 `s3` 模式都会进入 `/readyz`；远程授权或对象存储不可用时服务保持 not ready。

Dashboard 本地构建验证：

```bash
cd team_cloud_go/dashboard
npm test -- --run
npm run type-check
npm run build
```

### Docker Compose（历史验证资产）

`deploy/team-cloud/compose.yaml` 是 P1-P5 期间的历史验证资产，用于复跑 Python 参考实现相关测试；首次上线不再以 Python `team_cloud/` 作为 Team Cloud 服务端。需要本地验证 Go 服务时优先使用上方 `team_cloud_go` 命令。

```bash
docker compose -f deploy/team-cloud/compose.yaml up --build --wait
scripts/team-cloud-foundation-smoke.sh
```

安装前检查：

- `deploy/team-cloud/secrets/*.txt` 已准备。
- `TEAM_CLOUD_*_FILE` 指向的 secret 文件存在。
- 本地端口 `8780`、`8781`、`18000`、`50051`、`19000`、`19001` 未被占用。
- Casdoor redirect URL 与浏览器访问域名一致。
- SpiceDB pre-shared key 与 Team API 配置一致。
- MinIO bucket、access key、secret key 和 lifecycle 已初始化。
- PostgreSQL 18 数据卷挂载到 `/var/lib/postgresql`。

受限 registry 环境可覆盖镜像来源：

```bash
TEAM_CLOUD_PYTHON_BASE_IMAGE=mirror.gcr.io/library/python:3.13-slim-bookworm \
ALPINE_IMAGE=mirror.gcr.io/library/alpine:3.22.2 \
MINIO_IMAGE=quay.io/minio/minio:RELEASE.2025-09-07T16-13-09Z \
MINIO_MC_IMAGE=quay.io/minio/mc:RELEASE.2025-08-13T08-35-41Z \
MAILPIT_IMAGE=ghcr.io/axllent/mailpit:v1.29.5 \
TEAM_WEB_IMAGE=mirror.gcr.io/library/nginx:1.29.3-alpine \
docker compose -f deploy/team-cloud/compose.yaml up --build --wait
```

### Helm

适用于 Kubernetes staging/production。

Go 服务端 Helm chart 迁移完成前，生产安装使用 `team_cloud_go/deploy/kubernetes/team-cloud-go.yaml`。原 `deploy/team-cloud/helm/hermes-team-cloud` 保留为 P5 验证证据和后续 Helm 迁移参考。

```bash
helm upgrade --install hermes-team-cloud deploy/team-cloud/helm/hermes-team-cloud --atomic --wait
scripts/team-cloud-foundation-smoke.sh
```

GA 本地补审已完成 `helm lint`、`helm upgrade`、二次 upgrade 和 `helm rollback`。如果只验证 release 机制而不启动工作负载，可使用 P5-13 同款 smoke 参数：`replicaCount.*=0`、`jobs.*.enabled=false`、`persistence.enabled=false`。

### Offline bundle

适用于离线或受限网络环境。

```bash
scripts/team-cloud-offline-bundle.sh --manifest deploy/team-cloud/offline/manifest.yaml
deploy/team-cloud/offline/install.sh --manifest deploy/team-cloud/offline/manifest.yaml
scripts/team-cloud-foundation-smoke.sh
```

离线包必须包含：

- `team_cloud_go/Dockerfile`
- `team_cloud_go/deploy/kubernetes/team-cloud-go.yaml`
- `deploy/team-cloud/offline/manifest.yaml`
- 镜像目录
- checksums
- 安装脚本
- 对应版本的 release artifacts

### 首次初始化和登录

1. 打开 `http://<team-cloud-host>:8780/dashboard/`。
2. 在连接栏输入 Team Cloud API 地址和 service token。
3. 在“初始化”页刷新状态，确认 `initialized=false`。
4. 输入组织标识、组织名称、管理员邮箱和管理员用户 ID，创建超级管理员。
5. 在“组织”页创建团队并邀请至少一个管理员，避免单 Owner 风险。
6. 在“权限”页验证 `organization:<org>#owner@member:<member>` 和团队权限关系。
7. 配置 Casdoor 后，Org Owner 使用 Casdoor 登录 Team Web 或持有 Casdoor JWT 调用 API。
8. 打开 Web Chat，提交一次团队会话。
9. 运行 `scripts/team-cloud-foundation-smoke.sh`。

## 组织、团队和成员管理

管理员在 Team Cloud Go Dashboard 或 Team API 中完成组织、团队和成员操作。团队云端管理页面不放在本地 Hermes dashboard/CLI 中；本地 UI 只保存远程 Team Cloud 地址、token 和个人运行配置。

### 创建组织

Go 服务端 API 示例：

```bash
curl -sS -X POST "$TEAM_CLOUD_URL/api/organizations" \
  -H "Authorization: Bearer $TEAM_CLOUD_SERVICE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"slug":"hermes-labs","name":"Hermes Labs"}'
```

关键字段：

- `slug`：组织稳定标识，进入 SpiceDB resource id，不建议变更。
- `name`：展示名称。
- `owner`：初始组织所有者。

验证点：

- Team API 创建组织后写入 audit event。
- SpiceDB 中存在 `organization:<slug>#owner@user:<owner>`。
- Permission Explorer 可解释 owner 对组织、团队和项目的权限。

### 邀请成员

Go 服务端 API 示例：

```bash
curl -sS -X POST "$TEAM_CLOUD_URL/api/organizations/hermes-labs/members/invite" \
  -H "Authorization: Bearer $TEAM_CLOUD_SERVICE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@example.com","display_name":"Alice","user_id":"alice","role":"member"}'
```

成员生命周期：

1. `invite_member`：录入 email、display_name、user_id、role。
2. Casdoor 登录后完成 identity binding。
3. relationship outbox 写入 organization/team membership。
4. outbox worker 同步 SpiceDB。
5. 成员进入 Web Chat 或 Gateway/API 运行时。

禁用成员时：

- 管理 API 写入 disable 状态。
- relationship outbox 写入删除 intent。
- 后续权限 check fail closed。
- audit 保留 actor、target member、decision 和 request id。

### service account 和 PAT

机器调用使用 service account 或 PAT：

- PAT 只用于受控自动化和迁移脚本。
- service account 必须绑定组织、团队或项目最小权限。
- 不要把 PAT 写入 `config.yaml`；secret 进入 secret file 或安全凭据系统。
- 轮换后运行相关 API smoke。

## 设置团队成员的个人记忆环境

个人记忆是成员私有的长期记忆序列，scope 固定为 `personal`。TeamMemoryProvider 通过 `TeamContext` 确定当前成员和团队上下文。

### 前置条件

每个成员必须满足：

- 已在 Casdoor 登录并同步到 Team Cloud。
- 已绑定 organization membership。
- 已绑定 team membership。
- 已有 `member_id`。
- Web/API/Gateway 运行时可以解析 `org_id`、`team_id`、`project_id` 和 `member_id`。
- `personal_memory_enabled` 为 `True`，除非这是共享群聊或管理员显式关闭个人记忆。

TeamMemoryProvider 所需上下文：

```python
TeamContext(
    org_id="org-1",
    team_id="team-1",
    project_id="project-1",
    member_id="alice",
    personal_memory_enabled=True,
)
```

TeamMemoryProvider 配置：

```python
TeamMemoryProviderConfig(
    team_cloud_url="https://team-cloud.example",
    service_token="<service-token>",
    team_context=team_context,
    prefetch_limit=8,
)
```

### 开启个人记忆

1. 管理员确认成员未禁用。
2. 确认 Gateway/API identity resolver 可解析当前 actor。
3. 对单人会话设置 `personal_memory_enabled=True`。
4. 在 agent turn 开始前调用 `/v1/memory/prefetch`。
5. 在 agent turn 结束后通过 `/v1/memory/observations` 写入 observation。
6. extraction worker 从 observation 生成候选个人记忆。

### 成员可用工具

| 工具 | 用途 | 默认 scope |
| --- | --- | --- |
| `team_memory_search` | 搜索 personal 和 team_shared 记忆。 | personal + team_shared |
| `team_memory_remember` | 写入个人记忆。 | personal |
| `team_memory_propose` | 提交团队共享记忆候选。 | team_shared |
| `team_memory_promote` | 将个人记忆提升为团队共享候选。 | team_shared candidate |
| `team_memory_forget` | 归档记忆。 | personal 写权限 |
| `team_memory_backup_now` | 立即运行个人记忆备份。 | personal backup |

个人记忆写入权限使用 `memory.personal.write` 检查。权限被拒绝时返回 `permission_denied`，不会调用 Team Cloud 写接口。

### 成员自助操作

成员可以：

- 创建个人事实、偏好和项目上下文。
- 查询自己的 personal 记忆。
- 归档过期个人记忆。
- 恢复软删除记忆。
- 触发 `team_memory_backup_now`。
- 查看 restore preview，再决定是否执行恢复。

成员不能：

- 读取其他成员的 personal 记忆。
- 在共享群聊中默认注入个人记忆。
- 跳过 PII/secret detector。
- 将个人记忆直接写成 team_shared；必须走 propose/review。

## 配置团队共享记忆

团队共享记忆是组织或团队可见的事实序列，scope 固定为 `team_shared`。

### 适用内容

适合写入 team_shared 的内容：

- 团队约定
- 项目部署事实
- 客户交付上下文
- Runbook 入口
- 已审核的工具使用约束
- 团队所有成员都应该知道的长期事实

不适合写入 team_shared 的内容：

- 成员个人偏好
- 密钥、token、密码
- 未经授权的客户隐私信息
- 临时聊天噪声
- 未确认的猜测

### 提交流程

1. 成员调用 `team_memory_propose`，或使用 `team_memory_promote` 从个人记忆提升候选。
2. Team API 创建 `team_shared` 候选，默认进入 review queue。
3. duplicate/conflict detector 查重。
4. PII/secret detector 标记敏感内容。
5. 管理员或 reviewer 批准、拒绝或要求修改。
6. 批准后写入 SpiceDB memory relationship。
7. 后续 prefetch 先按 `query_embedding`/文本召回，再通过 `read_team` 授权检查过滤。

### Review queue

Review queue 处理动作：

- approve：候选进入 active team_shared。
- reject：候选结束，不进入召回。
- merge：与既有记忆合并。
- request_changes：要求提交者修订。
- escalate：升级给管理员或安全负责人。

Review 证据：

- audit event
- reviewer id
- decision
- conflict/PII 标记
- source trace

## 审计、授权和工具策略 API

Go 服务端新增治理 API：

```bash
curl -sS "$TEAM_CLOUD_URL/v1/audit/events?org_id=hermes-labs" \
  -H "Authorization: Bearer $TEAM_CLOUD_SERVICE_TOKEN"
```

写入授权关系：

```bash
curl -sS -X PUT "$TEAM_CLOUD_URL/v1/authz/relationships" \
  -H "Authorization: Bearer $TEAM_CLOUD_SERVICE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "org_id": "hermes-labs",
    "resource_type": "team",
    "resource_id": "hermes-labs:platform",
    "relation": "member",
    "subject_type": "member",
    "subject_id": "hermes-labs:alice",
    "idempotency_key": "team-platform-alice"
  }'
```

检查权限：

```bash
curl -sS -X POST "$TEAM_CLOUD_URL/v1/authz/check" \
  -H "Authorization: Bearer $TEAM_CLOUD_SERVICE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "org_id": "hermes-labs",
    "resource_type": "team",
    "resource_id": "hermes-labs:platform",
    "permission": "read",
    "subject_type": "member",
    "subject_id": "hermes-labs:alice"
  }'
```

工具策略评估：

```bash
curl -sS -X POST "$TEAM_CLOUD_URL/v1/tool-policy/evaluate" \
  -H "Authorization: Bearer $TEAM_CLOUD_SERVICE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"org_id":"hermes-labs","member_id":"hermes-labs:alice","tool_name":"terminal","risk_level":"destructive"}'
```

当前 Go 服务提供 `local` 和 `spicedb_http` 两种授权模式。生产部署使用 `TEAM_CLOUD_AUTHZ_MODE=spicedb_http` 接入远程 SpiceDB/Authzed compatible HTTP API；Go 版不依赖会提升 toolchain 的 gRPC SDK。

## 个人记忆与团队记忆两重记忆序列

运行时 prefetch 同时处理两条序列：

| 序列 | scope | 过滤方式 | 默认注入 |
| --- | --- | --- | --- |
| 个人记忆 | `personal` | `org_id + subject_member_id` | 单人会话注入 |
| 团队记忆 | `team_shared` | `org_id + team_id/project_id + SpiceDB read_team` | 团队上下文注入 |

prefetch 请求包含：

- `query`
- `query_embedding`
- `org_id`
- `member_id`
- `team_id`
- `project_id`
- `limit`
- `include_personal`

写入 memory 时可传入 `embedding`。Go 服务端 PostgreSQL schema 使用 pgvector `embedding vector(1536)`，prefetch 在提供 `query_embedding` 时按 cosine similarity 排序；不提供向量时回退到文本 token 匹配。

Go 服务端 API 示例：

```bash
curl -sS -X POST "$TEAM_CLOUD_URL/v1/memory/prefetch" \
  -H "Authorization: Bearer $TEAM_CLOUD_SERVICE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "deployment convention",
    "org_id": "hermes-labs",
    "member_id": "hermes-labs:alice",
    "team_id": "hermes-labs:platform",
    "project_id": "project-1",
    "include_personal": true,
    "limit": 8
  }'
```

共享群聊或无法明确 actor 的会话应设置：

```json
{
  "personal_memory_enabled": false
}
```

这样只召回 team_shared，避免个人记忆泄漏到共享上下文。

## 本地记忆定时备份

本地记忆定时备份覆盖个人记忆，不覆盖未授权团队共享内容。备份链路由 backup policy、backup job、encrypted JSONL exporter 和 MinIO manifest 组成。

### 配置备份策略

管理员或成员设置 personal backup policy：

- enabled：是否启用。
- schedule：定时周期。
- retention_days：保留天数。
- encryption_key_ref：加密密钥引用。
- target：MinIO bucket/object prefix。

备份策略写入 `backup_policies`，Go 服务端调度器按 `TEAM_CLOUD_BACKUP_SCHEDULER_INTERVAL_SECONDS` 扫描 enabled policy 并生成 `backup_jobs`。调度器尊重 `cadence`，只执行 `next_run_at` 已到期或尚未运行过的 policy；成功后写入 `last_run_at`/`next_run_at`。每次生成 backup job 后会按 `retention_count` 将更旧的 job 标记为 `pruned`。需要外部调度时，也可以保留 `TEAM_CLOUD_BACKUP_SCHEDULER_ENABLED=false`，由 Kubernetes CronJob 或运维工具调用 `POST /v1/backups/personal/run`。

Go 服务端当前提供个人备份策略 API：

```bash
curl -sS -X PUT "$TEAM_CLOUD_URL/v1/me/memory-backup-policy" \
  -H "Authorization: Bearer $TEAM_CLOUD_SERVICE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"org_id":"hermes-labs","member_id":"hermes-labs:alice","cadence":"daily","enabled":true,"retention_count":7}'
```

### 立即备份

成员可通过工具触发：

```json
{
  "tool": "team_memory_backup_now",
  "args": {}
}
```

TeamMemoryProvider 调用：

```text
POST /v1/backups/personal/run
```

请求上下文：

- `org_id`
- `member_id`

权限检查：

- action：`backup.create`
- actor：当前 member
- resource：personal backup

### 备份输出

备份输出为加密 JSONL：

- content
- memory_type
- sensitivity
- metadata
- checksum
- created_at
- source trace

对象写入 MinIO 后登记 object manifest。Go 服务端在 `TEAM_CLOUD_BACKUP_OBJECT_MODE=s3` 时生成 AES-256-GCM 加密 JSONL，通过 S3 Signature V4 path-style PUT 上传，并在 backup job manifest 中记录 `object_store`、`bucket`、`object_key`、`format`、`encryption` 和 `checksum_sha256`。restore preview/execute 会从 S3/MinIO 读取对象，校验 checksum，解密 JSONL 后刷新恢复快照；数据库中的 backup items 只是缓存和开发模式 fallback。

Go 服务端备份恢复 API：

```bash
curl -sS -X POST "$TEAM_CLOUD_URL/v1/backups/personal/run" \
  -H "Authorization: Bearer $TEAM_CLOUD_SERVICE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"org_id":"hermes-labs","member_id":"hermes-labs:alice"}'

curl -sS -X POST "$TEAM_CLOUD_URL/v1/backups/personal/$BACKUP_ID/restore-preview" \
  -H "Authorization: Bearer $TEAM_CLOUD_SERVICE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"member_id":"hermes-labs:alice","mode":"merge"}'

curl -sS -X POST "$TEAM_CLOUD_URL/v1/backups/personal/$BACKUP_ID/restore-execute" \
  -H "Authorization: Bearer $TEAM_CLOUD_SERVICE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"member_id":"hermes-labs:alice","mode":"merge"}'
```

## 备份恢复和组织导出

### Restore preview

恢复必须先 preview；Go 服务端会在 `tcg_restore_previews` 中记录 preview，未 preview 直接执行会返回 `restore_preview_required`：

1. 解密备份到 restore staging。
2. 校验 checksum。
3. 与现有 personal memory 比较。
4. 输出 action：create、skip、conflict。
5. 管理员或成员审阅 preview。

### Restore execute

执行恢复时选择模式：

- `merge`
- `overwrite`
- `archive_current_then_restore`

Go 服务端 `merge` 会跳过已存在的同内容 personal memory；`overwrite` 会先将当前 active personal memory 标记为 deleted，再恢复备份；`archive_current_then_restore` 会先将当前 active personal memory 标记为 archived，再恢复备份。

执行后写入：

- restore job
- memory audit event
- object manifest reference
- notification event

### 组织导出

组织导出由管理员发起，覆盖组织范围内允许导出的资源：

- organization metadata
- teams/projects
- approved team_shared memory
- cloud session summary
- SpiceDB relationship snapshot
- MinIO object manifest

导出不应包含其他成员的 personal memory，除非满足明确的数据治理授权。

Go 服务端组织导出：

```bash
curl -sS -X POST "$TEAM_CLOUD_URL/v1/exports/org" \
  -H "Authorization: Bearer $TEAM_CLOUD_SERVICE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"org_id":"hermes-labs"}'
```

返回值中 `personal_count` 必须为 `0`。

### 删除和保留

删除请求流程：

1. 创建 deletion request。
2. 校验 actor 权限。
3. 进入等待期或审批期。
4. hard delete worker 清理 PostgreSQL、SpiceDB、MinIO。
5. audit 保留删除证据。

retention policies 统一控制 memory、backup、audit 和 export 保留周期。

Go 服务端删除请求：

```bash
curl -sS -X POST "$TEAM_CLOUD_URL/v1/deletion-requests" \
  -H "Authorization: Bearer $TEAM_CLOUD_SERVICE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"org_id":"hermes-labs","target_member_id":"hermes-labs:alice","requested_by":"hermes-labs:alice","deletion_scope":"personal_memory","reason":"member requested deletion"}'

curl -sS -X POST "$TEAM_CLOUD_URL/v1/deletion-requests/$REQUEST_ID/execute" \
  -H "Authorization: Bearer $TEAM_CLOUD_SERVICE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"actor_member_id":"hermes-labs:alice"}'
```

## 权限、角色和 Permission Explorer

SpiceDB/Authzed 是生产权限判断源。Team Cloud API 对管理、记忆、工具、备份和导出操作执行权限检查；本地开发可使用 `TEAM_CLOUD_AUTHZ_MODE=local`。Go 服务端的高风险治理入口采用“先取资源归属，再按 JWT principal 授权”的模式：authz relationship 写入、audit 读取、review queue、backup detail、deletion execute、runtime event 和组织列表都不能只依赖请求体中的 org/member/actor 字段。

常见角色：

- owner：组织所有者。
- admin：组织或团队管理员。
- member：普通成员。
- guest：受限访问者。
- service_account：自动化账号。

Permission Explorer 用于解释：

- subject
- resource
- permission
- allowed/denied
- cache key
- relationship path
- deny reason

管理员应在以下场景使用 Permission Explorer：

- 成员无法访问团队项目。
- team_shared 记忆未被召回。
- 工具调用被拒绝。
- service account 自动化失败。
- 禁用成员仍疑似有访问权。

## 工具策略、高危审批和 break-glass

工具策略基于 tool risk taxonomy 和 TeamToolPolicyHook。

风险分类：

- low
- medium
- high
- critical

高危工具流程：

1. classify tool call。
2. 查询组织工具策略。
3. 调 SpiceDB 检查 `tool.execute`。
4. 如需审批，创建 approval request。
5. 审批通过后执行。
6. 写入 tool audit。

break-glass 仅用于紧急运维：

- 必须有原因。
- 必须有过期时间。
- 必须通知管理员。
- 必须写审计。
- 结束后复盘。

## 迁移 SessionDB 和 legacy memory provider

### SessionDB 迁移

SessionDB 导入使用：

```bash
scripts/team-cloud-import-sessiondb.py \
  --db ~/.hermes/state.db \
  --org-id org-1 \
  --team-id team-1 \
  --project-id project-1 \
  --identity-map identity-map.json \
  --dry-run
```

`identity_map` 将本地 user id 映射为 Team Cloud `member_id`：

```json
{
  "alice-local-user-id": "team-cloud-member-id"
}
```

规则：

- 未映射 identity 不导入。
- `--dry-run` 只输出报告。
- 导入后 cloud session 使用 `source_platform=sessiondb:<source>`。
- 导入前先完成 backup。

### legacy memory provider 迁移

旧 provider 先导出为 JSONL，每行至少包含：

- content
- scope
- member_id
- team_id
- metadata

scope 映射：

- member-owned facts -> `personal`
- organization-approved shared facts -> `team_shared`

迁移前必须运行：

- unmapped identity report
- duplicate/conflict review
- PII/secret scan
- isolation smoke
- backup before cutover

## Deployment smoke 和 GA 验证

GA 验证入口：

```bash
scripts/team-cloud-foundation-smoke.sh
```

该 smoke 覆盖：

- P1 平台基础
- P2 双层记忆和 runtime
- P3 数据治理和权限硬化
- P4 Beta 验证
- P5 GA 发布包
- releaseManual 验收

发布前还应检查：

- `teamDoc/GAStep/progress-tracker.md` 中 P5 和 M5 为 Done。
- `teamDoc/GADoc/artifacts/release/team-cloud-ga-sign-off-v0.json` 中 `gate=ga`。
- final regression artifact 存在。
- deployment smoke artifact 存在。
- legal/compliance artifact 存在。
- post-GA backlog 均为 non-blocking。

## 运维、支持和 Post-GA backlog

### 日常检查

每日：

- Team API health/readiness。
- Casdoor OIDC discovery。
- SpiceDB schema/check latency。
- PostgreSQL migration status。
- MinIO bucket/manifest。
- backup job failure。
- audit/event backlog。

每周：

- 权限矩阵抽查。
- team_shared review queue backlog。
- backup restore drill 抽样。
- tool audit 高危调用复盘。
- cost/quotas dashboard。

### 支持流程

常见问题入口：

- 登录失败：检查 Casdoor issuer、redirect URL、JWKS。
- 权限拒绝：用 Permission Explorer 复现 subject/resource/permission。
- 个人记忆不召回：检查 `personal_memory_enabled`、member_id、scope 和 prefetch response。
- 团队记忆不召回：检查 review 状态、team_id/project_id、SpiceDB read_team。
- 备份失败：检查 backup policy、encryption key、MinIO manifest 和 notification。
- 迁移失败：检查 `identity_map` 和 dry-run unmapped report。

### Post-GA backlog

当前 Post-GA backlog 均为 non-blocking：

- `helm_runtime_lint_ci`
- `advanced_admin_analytics`
- `memory_quality_iteration`
- `external_audit_packet`

这些项目不阻塞 GA，可按运营优先级排期。

## 附录：关键命令

```bash
cd team_cloud_go && go test ./...
cd team_cloud_go && go vet ./...
scripts/team-cloud-foundation-smoke.sh
scripts/team-cloud-import-sessiondb.py --dry-run --db ~/.hermes/state.db --org-id org-1 --team-id team-1 --project-id project-1 --identity-map identity-map.json
scripts/team-cloud-ga-sign-off.py --output teamDoc/GADoc/artifacts/release/team-cloud-ga-sign-off-v0.json
scripts/team-cloud-post-ga-backlog.py --output teamDoc/GADoc/artifacts/release/team-cloud-post-ga-backlog-v0.json
```

## 附录：关键文档

- `teamDoc/GADoc/P5-03-install-guide.md`
- `teamDoc/GADoc/P5-04-admin-user-manuals.md`
- `teamDoc/GADoc/P5-06-runbook-summary.md`
- `teamDoc/GADoc/P5-10-migration-guide.md`
- `teamDoc/GADoc/P5-12-final-regression.md`
- `teamDoc/GADoc/P5-13-deployment-smoke.md`
- `teamDoc/GADoc/P5-14-legal-compliance-package.md`
- `teamDoc/GADoc/P5-15-post-ga-backlog.md`
- `teamDoc/GAStep/progress-tracker.md`
