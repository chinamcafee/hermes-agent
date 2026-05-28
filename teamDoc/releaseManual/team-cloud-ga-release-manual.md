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
- 可选 MinIO/S3-compatible 团队记忆和团队父人格备份对象
- Team Cloud Go 服务端、Team API、`/dashboard/` 管理台、Web Chat、Gateway/API identity headers
- TeamMemoryProvider 团队共享记忆接入
- CLI `/cloud-backup memory|soul` 本地个人记忆和本地人格定时备份、恢复、组织导出、删除和保留策略
- 工具策略、高危审批、break-glass 和审计
- 历史数据导入策略
- Deployment smoke 和 GA 验证
- 运维、支持和 Post-GA backlog

本地 Kubernetes 全栈演练另见 [Team Cloud Go + Dashboard minikube 本地 Kubernetes 部署手册](team-cloud-go-minikube-dashboard-manual.md)。

## 企业版团队功能开箱即用

Team Cloud 的默认拓扑由以下组件组成：

| 组件 | 用途 | 关键验证 |
| --- | --- | --- |
| Casdoor/JWKS | 组织登录 token 校验、issuer/audience/expiration 校验。 | `team_cloud/internal/httpapi/ga_capabilities_test.go`、`team_cloud/internal/authn` |
| SpiceDB/Authzed HTTP | 组织、成员、记忆、工具和备份权限关系。 | `team_cloud/internal/authz/spicedb_http_test.go`、`team_cloud/internal/httpapi/ga_capabilities_test.go` |
| PostgreSQL/pgvector | Team Cloud 主库、memory schema、embedding 检索；Go 服务端使用 `embedding vector(1536)` 和 `query_embedding`。 | `team_cloud/internal/store/postgres/schema_test.go`、`team_cloud/internal/httpapi/server_test.go` |
| MinIO/S3-compatible | 可选团队记忆和团队父人格备份对象存储；CLI 本地 memory/soul 备份由用户自行配置对象存储。 | `team_cloud/internal/objectstore`、`tests/hermes_cli/test_cloud_backup_cli.py` |
| Team Cloud Go API | 组织/成员 API、团队 memory API、团队父人格 API、review queue、团队级备份管理 API、bootstrap API，首次上线默认服务端。 | `cd team_cloud && go test ./...`、`cd team_cloud && go vet ./...` |
| Team Cloud Go Dashboard | `/dashboard/` 静态管理台，覆盖独立初始化引导、超级管理员登录、单团队成员、权限、记忆治理、团队父人格治理、备份和审计。 | `cd team_cloud/dashboard && npm test -- --run`、`npm run type-check`、`npm run build` |
| Gateway/API identity resolver | 消息平台和 API server 的团队身份注入。 | `tests/gateway/test_api_server_team_headers.py`、`tests/gateway/test_gateway_team_identity_resolver.py` |

默认上线顺序：

1. 构建并部署 `team_cloud/` Go 服务端和随镜像发布的 Dashboard。
2. 完成 Casdoor issuer、client、redirect URL 和 JWKS 配置。
3. 加载 SpiceDB schema，确认 pre-shared key 与 Team API secret 一致。
4. 执行 PostgreSQL migration，确认 pgvector extension 可用。
5. 如需团队记忆对象备份，初始化可选 MinIO/S3 bucket、manifest 和 lifecycle。
6. 打开 `/dashboard/`，确认 PostgreSQL、Redis 已由 Secret/env 注入并 ready；对象存储未配置时显示 optional。
7. 在独立 Step-by-Step 初始化引导页创建单团队空间和唯一超级管理员。
8. 使用超级管理员帐号密码登录 Dashboard，在团队成员页创建管理员和用户。
9. 运行 `cd team_cloud && go test ./...`、`go vet ./...`、`cd dashboard && npm test -- --run && npm run build` 留存 Go 服务端和 Dashboard 证据。
10. 运行 `scripts/team-cloud-foundation-smoke.sh` 留存 Hermes runtime 集成证据。

## 安装和首次登录

### Go 服务端 Kubernetes 部署

首次上线推荐部署 `team_cloud/` Go 服务端；旧 Python 服务端已经删除。

```bash
cd team_cloud
docker build -t ghcr.io/hermes-agent/team-cloud-go:0.1.0 .
kubectl apply -f deploy/kubernetes/team-cloud-go.yaml
kubectl rollout status deployment/hermes-team-cloud-go
```

Go 服务端镜像包含 `team_cloud/dashboard/` 的 Next.js static export。部署完成后：

```bash
kubectl port-forward svc/hermes-team-cloud-go 8780:8780
open http://localhost:8780/dashboard/
```

Dashboard V2 首次初始化调用：

- `GET /v1/bootstrap/status` 检查服务、后端、授权、PostgreSQL、可选对象存储、团队空间和超级管理员状态。
- `POST /v1/bootstrap/super-admin` 在未初始化状态下开放调用，创建单团队空间和唯一 `super_admin`。
- `POST /v1/auth/login` 使用 `super_admin` 或 `admin` 帐号密码换取 Redis 支撑的 `hcs_...` Dashboard session token。
- 已经存在 `super_admin` 后，bootstrap 会返回 `409 already_initialized`，后续成员通过“团队成员”页面直接创建。

部署前必须替换 Kubernetes Secret：

- `TEAM_CLOUD_DATABASE_URL`
- `TEAM_CLOUD_REDIS_PASSWORD`
- `TEAM_CLOUD_DASHBOARD_ENABLED=true`
- `TEAM_CLOUD_DASHBOARD_DIR=/usr/share/team-cloud-go/dashboard`

生产环境要求：

- `TEAM_CLOUD_DATABASE_URL` 指向 PostgreSQL。
- `TEAM_CLOUD_REDIS_ADDR` 指向 Redis，`TEAM_CLOUD_REDIS_PASSWORD` 由 Secret 注入。
- `TEAM_CLOUD_AUTO_MIGRATE=true` 仅用于首发和受控升级；严格变更窗口可改为 `false` 并由迁移 Job 执行。
- `/readyz` 返回 `ready` 后再接入 Hermes runtime 和 Gateway。
- `/dashboard/` 能返回管理台 HTML，未知 Dashboard 子路径能回退到静态 `index.html`。

Go 服务端本地验证：

```bash
cd team_cloud
TEAM_CLOUD_DATABASE_URL='postgres://hermes:secret@localhost:5432/hermes_team_cloud?sslmode=disable' \
TEAM_CLOUD_REDIS_ADDR='localhost:6379' \
go run ./cmd/team-cloud-server
```

Casdoor JWT 配置：

```bash
TEAM_CLOUD_CASDOOR_ISSUER=https://casdoor.example
TEAM_CLOUD_CASDOOR_AUDIENCE=hermes-team-cloud
TEAM_CLOUD_CASDOOR_JWKS_URL=https://casdoor.example/.well-known/jwks
```

配置后，Team Cloud Go 会按 JWKS 校验 RS256 Bearer token 的签名、issuer、audience 和 expiration。Dashboard 登录态使用 Redis session token。

远程授权和可选团队记忆备份对象配置：

```bash
TEAM_CLOUD_AUTHZ_MODE=spicedb_http
TEAM_CLOUD_AUTHZ_ENDPOINT=http://spicedb:8443
TEAM_CLOUD_AUTHZ_TOKEN=change-me

TEAM_CLOUD_BACKUP_OBJECT_MODE=s3
TEAM_CLOUD_BACKUP_S3_ENDPOINT=http://minio:9000
TEAM_CLOUD_BACKUP_S3_BUCKET=hermes-team-memory-backups
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
cd team_cloud/dashboard
npm test -- --run
npm run type-check
npm run build
```

### 本地 Smoke 脚本

```bash
scripts/team-cloud-smoke.sh
scripts/team-cloud-foundation-smoke.sh
scripts/team-cloud-isolation-smoke.sh
```

安装前检查：

- `team_cloud/` 能构建 Go 服务端和 Dashboard。
- 本地端口 `8780`、`50051`、`5432`、`6379`、`9000` 未被占用，具体取决于是否启动外部 PostgreSQL、Redis、SpiceDB 和可选 MinIO。
- Casdoor redirect URL 与浏览器访问域名一致。
- SpiceDB pre-shared key 与 Team API 配置一致。
- 如启用团队记忆对象备份，MinIO/S3 bucket、access key、secret key 和 lifecycle 已初始化。
- PostgreSQL 18 数据卷挂载到 `/var/lib/postgresql`，minikube 手册中的 StatefulSet 已按此路径配置。

### Kubernetes Manifest

适用于 Kubernetes staging/production。

当前生产安装入口是 `team_cloud/deploy/kubernetes/team-cloud-go.yaml`。旧 Python compose/Helm/offline 资产已经删除，不再作为 GA 安装路径。

```bash
kubectl apply -f team_cloud/deploy/kubernetes/team-cloud-go.yaml
kubectl rollout status deployment/hermes-team-cloud-go -n hermes-team-cloud --timeout=180s
scripts/team-cloud-foundation-smoke.sh
```

### Offline bundle

适用于离线或受限网络环境。

```bash
scripts/team-cloud-offline-bundle.sh
scripts/team-cloud-foundation-smoke.sh
```

离线包必须包含：

- `team_cloud/Dockerfile`
- `team_cloud/deploy/kubernetes/team-cloud-go.yaml`
- `team_cloud/README.md`
- release manual 和 minikube manual
- 可选镜像目录（通过 `OFFLINE_IMAGES` 导出）
- checksums
- 对应版本的 release artifacts

### 首次初始化和登录

1. 打开 `http://<team-cloud-host>:8780/dashboard/`。
2. 如果引导页显示 PostgreSQL 或 Redis 未配置，先修复 Kubernetes Secret/env 并重启服务；Dashboard 不再保存连接配置。对象存储是可选状态，不阻塞初始化。
3. 在 Step-by-Step 初始化引导页输入团队名、超级管理员邮箱、帐号和密码，创建唯一超级管理员。
4. 初始化完成后使用超级管理员帐号密码登录管理台。
5. 在“团队成员”页直接创建至少一个管理员和必要用户。
6. 在“权限中心”页查看服务端写死的 super_admin/admin/user 角色能力矩阵。
7. 配置 Casdoor 后，管理员可持有 Casdoor JWT 调用 API。
8. 打开 Web Chat，提交一次团队会话。
9. 运行 `scripts/team-cloud-foundation-smoke.sh`。

## 组织、团队和成员管理

管理员在 Team Cloud Go Dashboard 或 Team API 中完成团队和成员操作。第一版 Dashboard 只暴露单团队模型，不把多组织、多租户作为显性页面层级；内部 `org_id` 保留为后续扩展和 API 兼容字段。团队云端管理页面不放在本地 Hermes dashboard/CLI/Desktop 中；本地 UI 只通过 Hermes Agent Bridge 保存远程 Team Cloud 地址、token 和个人运行配置。

### 创建组织

Go 服务端 API 示例：

先用 Dashboard 管理帐号换取用户级 token：

```bash
export TEAM_CLOUD_DASHBOARD_TOKEN="$(
  curl -sS -X POST "$TEAM_CLOUD_URL/v1/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"org_id":"hermes-labs","user_id":"owner","password":"<password>"}' \
    | python -c 'import json,sys; print(json.load(sys.stdin)["token"])'
)"
```

```bash
curl -sS -X POST "$TEAM_CLOUD_URL/api/organizations" \
  -H "Authorization: Bearer $TEAM_CLOUD_DASHBOARD_TOKEN" \
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

### 创建成员

Go 服务端 API 示例：

```bash
curl -sS -X POST "$TEAM_CLOUD_URL/api/organizations/hermes-labs/members" \
  -H "Authorization: Bearer $DASHBOARD_SESSION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@example.com","display_name":"Alice","user_id":"alice","role":"user","password":"change-me"}'
```

成员生命周期：

1. `create_member`：超级管理员创建管理员或用户；管理员只能创建用户。
2. 服务端保存密码 hash，API 不返回 hash。
3. 成员页支持按帐号、邮箱和显示名查询，按角色筛选，编辑邮箱/显示名。
4. 服务端写入 organization/team relationship。
5. 成员随后配置 Hermes CLI/dashboard 连接 Team Cloud。
6. 兼容 API `/members/invite` 仍保留给外部邀请流程，但不是 Dashboard V2 主路径。

### Hermes CLI 连接 Team Cloud

管理员在 Dashboard 创建成员后，成员在本地 Hermes profile 内执行：

```bash
hermes team connect https://team-cloud.example.com
hermes team login --org hermes-labs --user alice --project default
hermes team status
hermes
```

本地开发或 minikube 环境：

```bash
kubectl -n hermes-team-cloud port-forward svc/team-cloud-go 8780:8780
hermes team connect http://localhost:8780
hermes team login --org hermes-labs --user alice --project default
```

交互式 CLI 中也可以使用 slash command：

```text
/team status
/team connect http://localhost:8780
/team login hermes-labs alice hermes-labs default
/team off
/team logout
```

CLI 配置边界：

- `config.yaml` 的 `team_cloud` 段只保存 URL、默认 org/team/project/member 和 API 熔断状态。
- 登录 session token 写入 profile `.env` 的 `HERMES_TEAM_CLOUD_SESSION_TOKEN`。
- `hermes team off` 只关闭团队模式，不删除 token。
- `hermes team logout` 删除本地 token 并关闭团队模式。
- CLI、TUI、oneshot 和 background agent 都会在配置完整时把 `team_context` 传给 `AIAgent`。
- 普通 `user` 可以登录 CLI；Dashboard 管理页仍只允许 `super_admin/admin`。
- 个人记忆和本地人格不进入 Team Cloud 云端管理；本地备份使用 `/cloud-backup memory|soul`。
- 团队父人格只能由 Team Cloud Dashboard 的“团队父人格中心”管理；CLI/Desktop 保存本地人格时，若处于 team mode，会触发 Hermes Agent 使用当前 profile 配置的大模型供应商合并团队父人格和本地人格。
- Team mode 可用性必须同时满足 Team Cloud URL 已配置、成员帐号登录成功、session 校验通过、默认 org/member context 存在且熔断器未阻断。只配置 URL 但未登录时，CLI/Desktop 应显示 login required/local，不得显示 Team mode active。
- team mode 下即使团队父人格尚未配置正文，CLI/Desktop 也应展示团队父人格、本地人格、合并后人格三段；合并后人格等于本地人格并标记 `team_parent_missing`。
- 如果没有配置模型供应商，或供应商不可用，本地人格保存仍成功；CLI/Desktop 应显示合并失败提示，并使用安全降级组合保证团队父人格仍优先。

禁用成员时：

- 管理 API 写入 disable 状态。
- 唯一超级管理员不可被停用。
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

个人记忆是成员本地 Hermes profile 的长期记忆序列，不由 Team Cloud 云端保存、查询或备份。成员加入团队后，Team Cloud 只提供团队身份、团队记忆和团队记忆治理；个人记忆继续由 Hermes 本地记忆系统处理。

成员侧准备：

1. 确认当前 `HERMES_HOME` 或 profile 是自己的个人环境。
2. 正常使用 Hermes 内置个人记忆能力。
3. 如需备份，执行 `/cloud-backup config` 配置 MinIO/S3-compatible 地址。
4. 执行 `/cloud-backup memory schedule daily|weekly|monthly` 设置本地个人记忆周期备份，或 `/cloud-backup memory backup` 手动触发。
5. 执行 `/cloud-backup soul schedule daily|weekly|monthly` 设置本地人格周期备份，或 `/cloud-backup soul backup` 手动触发。
6. 需要恢复时，先确认目标 profile，再执行 `/cloud-backup memory restore <object-key>` 或 `/cloud-backup soul restore <object-key>`。

Team Cloud CLI provider 不暴露 `team_memory_remember` 或 `team_memory_backup_now`。这些能力已经被本地个人记忆、团队记忆 Dashboard 和 `/cloud-backup` 取代。

### TeamMemoryProvider 上下文

```python
TeamContext(
    org_id="org-1",
    team_id="team-1",
    project_id="project-1",
    member_id="alice",
)
```

```python
TeamMemoryProviderConfig(
    team_cloud_url="https://team-cloud.example",
    service_token="<member-session-token>",
    team_context=team_context,
    prefetch_limit=8,
)
```

### 成员可用团队记忆工具

| 工具 | 用途 | 默认 scope |
| --- | --- | --- |
| `team_memory_search` | 搜索 team_shared 团队记忆。 | team_shared |
| `team_memory_add` | 用户明确要求新增团队记忆时，直接创建 active 团队共享记忆。 | team_shared |
| `team_memory_propose` | 提交团队共享记忆待审核候选。 | team_shared pending_review |
| `team_memory_promote` | 将候选记忆提交到团队审核流。 | team_shared candidate |
| `team_memory_forget` | 归档团队记忆。 | team_shared |

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

1. 管理员/具备 `write_team` 权限的成员如果明确要新增生效团队记忆，调用 `team_memory_add`，直接创建 `status=active` 的 `team_shared` 记忆。
2. 需要审核时，成员调用 `team_memory_propose`，提交团队记忆候选。
3. Team API 创建 `team_shared` 候选，默认进入 review queue。
4. duplicate/conflict detector 查重。
5. PII/secret detector 标记敏感内容。
6. 管理员或 reviewer 批准、拒绝或要求修改。
7. 批准后写入 SpiceDB memory relationship。
8. 后续 prefetch 先按 `query_embedding`/文本召回，再通过 `read_team` 授权检查过滤。

### 自动抽取触发边界

当前 Go 服务端区分三件事：

- 显式新增：用户明确要求“增加团队记忆”时，CLI team mode 中的模型应调用 `team_memory_add`，立即写入 `/v1/memory`，Dashboard active 列表可见。
- Observation 上报：每个完整、未中断的 agent turn 结束后，`TeamMemoryProvider.sync_turn()` 调用 `/v1/memory/observations`。这一步自动触发，但它只创建 `pending` observation。
- 自动抽取生成记忆：需要 extraction worker 或离线任务消费 observation 后再写入 `source_type=auto_extracted` 的 memory item。当前 Go 首发服务端尚未内置常驻 worker，因此普通对话不会仅因为 observation 上报就自动出现在 Dashboard 记忆治理列表中。

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

### Dashboard 记忆治理

Team Cloud Go Dashboard 的“记忆治理”页用于管理已经进入团队记忆库的 `team_shared` 记忆：

- 团队记忆库列表展示内容、状态、版本、`memory_type`、`sensitivity` 和来源标签。
- 自动抽取记忆使用 `source_type=auto_extracted`，并通过 `source_member_id` 标记来源成员。
- 管理员创建记忆使用 `source_type=admin_created`，并通过 `created_by_member_id` 标记创建者。
- 管理员点击“新建团队记忆”后，在弹窗中创建 `status=active` 的团队记忆。
- 管理员点击列表行“编辑”后，在弹窗中编辑任意团队记忆的内容、类型和敏感度。
- 列表行“停用”会把状态改为 `archived`，不会删除数据。
- 列表行“删除”会调用 `DELETE /v1/memory/{id}`，从服务端硬删除该记忆及关联 review 记录。
- 待审队列行“审核”会打开审核弹窗，批准或拒绝都在弹窗中完成。

对应 API：

```bash
curl -sS "$TEAM_CLOUD_URL/v1/memory?org_id=hermes-labs&scope=team_shared&status=active" \
  -H "Authorization: Bearer $TEAM_CLOUD_DASHBOARD_TOKEN"

curl -sS -X POST "$TEAM_CLOUD_URL/v1/memory" \
  -H "Authorization: Bearer $TEAM_CLOUD_DASHBOARD_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"org_id":"hermes-labs","scope":"team_shared","status":"active","source_type":"admin_created","memory_type":"policy","sensitivity":"normal","content":"生产事故首响阶段必须明确 owner。"}'

curl -sS -X PATCH "$TEAM_CLOUD_URL/v1/memory/mem-123" \
  -H "Authorization: Bearer $TEAM_CLOUD_DASHBOARD_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content":"生产事故首响阶段必须明确 accountable owner。","memory_type":"policy","sensitivity":"normal"}'

curl -sS -X POST "$TEAM_CLOUD_URL/v1/memory/mem-123/disable" \
  -H "Authorization: Bearer $TEAM_CLOUD_DASHBOARD_TOKEN"

curl -sS -X DELETE "$TEAM_CLOUD_URL/v1/memory/mem-123" \
  -H "Authorization: Bearer $TEAM_CLOUD_DASHBOARD_TOKEN"
```

## 审计、授权和工具策略 API

Go 服务端新增治理 API：

```bash
curl -sS "$TEAM_CLOUD_URL/v1/audit/events?org_id=hermes-labs" \
  -H "Authorization: Bearer $TEAM_CLOUD_DASHBOARD_TOKEN"
```

写入授权关系：

```bash
curl -sS -X PUT "$TEAM_CLOUD_URL/v1/authz/relationships" \
  -H "Authorization: Bearer $TEAM_CLOUD_DASHBOARD_TOKEN" \
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
  -H "Authorization: Bearer $TEAM_CLOUD_DASHBOARD_TOKEN" \
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
  -H "Authorization: Bearer $TEAM_CLOUD_DASHBOARD_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"org_id":"hermes-labs","member_id":"hermes-labs:alice","tool_name":"terminal","risk_level":"destructive"}'
```

当前 Go 服务提供 `local` 和 `spicedb_http` 两种授权模式。生产部署使用 `TEAM_CLOUD_AUTHZ_MODE=spicedb_http` 接入远程 SpiceDB/Authzed compatible HTTP API；Go 版不依赖会提升 toolchain 的 gRPC SDK。

## 个人记忆与团队记忆运行时边界

运行时存在两条记忆序列，但职责不同：

| 序列 | 存储位置 | 查询方式 | 默认注入 |
| --- | --- | --- | --- |
| 个人记忆 | 本地 Hermes profile `memories/` | Hermes 本地记忆系统 | 当前个人会话 |
| 团队记忆 | Team Cloud Go PostgreSQL `team_shared` | TeamMemoryProvider 调用 `/v1/memory/prefetch` | 团队上下文 |

Team Cloud prefetch 请求包含：

- `query`
- `query_embedding`
- `org_id`
- `member_id`
- `team_id`
- `project_id`
- `limit`
- `include_personal=false`

### 自动查询和加载时机

Team Cloud 记忆加载发生在每个 agent turn 的模型调用前：

1. `AIAgent.run_conversation()` 收到用户消息后，先调用 `MemoryManager.on_turn_start()`。
2. 随后调用 `MemoryManager.prefetch_all(original_user_message)`。
3. `TeamMemoryProvider.prefetch()` 调用 Team Cloud Go `/v1/memory/prefetch`。
4. 服务端按 `team_id/project_id` 和 `read_team` 权限返回 team_shared 记忆。
5. 返回结果被格式化为 `Team Cloud memory`，再包进 `<memory-context>` 注入本轮消息上下文。
6. 中断 turn 不会在结束时写 observation；成功完成的 turn 会在最后调用 `sync_turn()` 和 `queue_prefetch_all()`。

写入 memory 时可传入 `embedding`。Go 服务端 PostgreSQL schema 使用 pgvector `embedding vector(1536)`，prefetch 在提供 `query_embedding` 时按 cosine similarity 排序；不提供向量时回退到文本 token 匹配。

Go 服务端 API 示例：

```bash
curl -sS -X POST "$TEAM_CLOUD_URL/v1/memory/prefetch" \
  -H "Authorization: Bearer $TEAM_CLOUD_DASHBOARD_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "deployment convention",
    "org_id": "hermes-labs",
    "member_id": "hermes-labs:alice",
    "team_id": "hermes-labs:platform",
    "project_id": "project-1",
    "include_personal": false,
    "limit": 8
  }'
```

这样 Team Cloud 只召回 team_shared，避免个人记忆进入云端团队上下文。

## 本地 memory/soul 定时备份

本地个人记忆和本地人格备份由 Hermes CLI `/cloud-backup` 负责，不经过 Team Cloud：

```text
/cloud-backup status
/cloud-backup config --endpoint http://minio.local:9000 --bucket hermes-personal-backups --region us-east-1 --root-prefix alice
/cloud-backup memory schedule weekly
/cloud-backup memory backup
/cloud-backup memory history
/cloud-backup memory restore alice/profiles/default/memory/2026/05/20260524T084500Z-personal-memory.json
/cloud-backup soul schedule weekly
/cloud-backup soul backup
/cloud-backup soul history
/cloud-backup soul restore alice/profiles/default/soul/2026/05/20260524T084500Z-local-soul.json
```

同样能力也可以使用顶层命令：

```bash
hermes cloud-backup status
hermes cloud-backup memory backup
hermes cloud-backup soul backup
hermes cloud-backup memory history
hermes cloud-backup soul history
```

备份对象格式为 `hermes-cloud-backup-memory-v1` 和 `hermes-cloud-backup-soul-v1` JSON。memory 内容来自当前 profile 的 `memories/` 目录，soul 内容来自当前 profile 的 `SOUL.md`。恢复会写回当前 profile，因此恢复前必须确认 `HERMES_HOME` 或当前 profile。

## 团队级备份管理

Team Cloud Dashboard “备份管理”只管理团队级资源，不管理成员个人记忆或本地人格。当前包含两类备份：

- 团队记忆：读取/保存策略、查看历史、立即备份、先 preview 再 restore execute。
- 团队父人格：读取/保存策略、查看历史、立即备份、先 preview 再 restore execute。

团队父人格正文的创建和编辑不在“备份管理”中完成，而是在 Dashboard 左侧“团队父人格中心”中完成。该中心展示管理态内容、runtime 读取结果、版本、checksum、更新时间和更新人；备份管理只负责备份策略、历史、立即备份和恢复。

Go 服务端团队记忆备份 API：

```bash
curl -sS -X PUT "$TEAM_CLOUD_URL/v1/team-memory-backup-policy" \
  -H "Authorization: Bearer $TEAM_CLOUD_DASHBOARD_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"org_id":"hermes-labs","cadence":"daily","enabled":true,"retention_count":7}'

curl -sS -X POST "$TEAM_CLOUD_URL/v1/backups/team/run" \
  -H "Authorization: Bearer $TEAM_CLOUD_DASHBOARD_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"org_id":"hermes-labs"}'

curl -sS "$TEAM_CLOUD_URL/v1/backups/team?org_id=hermes-labs" \
  -H "Authorization: Bearer $TEAM_CLOUD_DASHBOARD_TOKEN"

curl -sS -X POST "$TEAM_CLOUD_URL/v1/backups/team/$BACKUP_ID/restore-preview" \
  -H "Authorization: Bearer $TEAM_CLOUD_DASHBOARD_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"org_id":"hermes-labs","mode":"merge"}'

curl -sS -X POST "$TEAM_CLOUD_URL/v1/backups/team/$BACKUP_ID/restore-execute" \
  -H "Authorization: Bearer $TEAM_CLOUD_DASHBOARD_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"org_id":"hermes-labs","mode":"merge"}'
```

恢复按团队记忆原始 `id` 做 insert-or-update；同一备份多次恢复不会在 PostgreSQL 中产生同 id 的重复记录。

Go 服务端团队父人格备份 API：

```bash
curl -sS -X PUT "$TEAM_CLOUD_URL/v1/team-soul-backup-policy" \
  -H "Authorization: Bearer $TEAM_CLOUD_DASHBOARD_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"org_id":"hermes-labs","cadence":"weekly","enabled":true,"retention_count":3}'

curl -sS -X POST "$TEAM_CLOUD_URL/v1/backups/team-soul/run" \
  -H "Authorization: Bearer $TEAM_CLOUD_DASHBOARD_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"org_id":"hermes-labs","team_id":"hermes-labs"}'

curl -sS "$TEAM_CLOUD_URL/v1/backups/team-soul?org_id=hermes-labs" \
  -H "Authorization: Bearer $TEAM_CLOUD_DASHBOARD_TOKEN"

curl -sS -X POST "$TEAM_CLOUD_URL/v1/backups/team-soul/$SOUL_BACKUP_ID/restore-preview" \
  -H "Authorization: Bearer $TEAM_CLOUD_DASHBOARD_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"org_id":"hermes-labs","mode":"merge"}'

curl -sS -X POST "$TEAM_CLOUD_URL/v1/backups/team-soul/$SOUL_BACKUP_ID/restore-execute" \
  -H "Authorization: Bearer $TEAM_CLOUD_DASHBOARD_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"org_id":"hermes-labs","mode":"merge"}'
```

团队父人格恢复按 `org_id + team_id` 更新 active soul，不会生成多个 active 父人格版本。

## 备份恢复和组织导出

### Restore preview

恢复必须先 preview；Go 服务端会在 `tcg_restore_previews` 中记录 preview，未 preview 直接执行会返回 `restore_preview_required`：

1. 解密备份到 restore staging。
2. 校验 checksum。
3. 与现有 team_shared memory 的原始 `id` 比较。
4. 输出 action：insert、update、skip。
5. API 调用方可以审阅 preview 响应；Dashboard 会在恢复操作中自动先调用 preview gate，再执行 restore execute。

### Restore execute

执行恢复时选择模式：

- `merge`
- `overwrite`
- `archive_current_then_restore`

Go 服务端 `merge` 以团队记忆原始 `id` 为唯一键执行 insert-or-update；`overwrite` 会先将当前 active team_shared memory 标记为 deleted，再恢复备份；`archive_current_then_restore` 会先将当前 active team_shared memory 标记为 archived，再恢复备份。团队父人格恢复使用同样的 preview gate，并按 `org_id + team_id` upsert active soul。

执行后写入：

- restore job
- memory audit event
- object manifest reference
- notification event

### 组织导出

组织导出由管理员发起，覆盖组织范围内允许导出的资源：

- organization metadata
- team-space metadata and projects
- approved team_shared memory
- cloud session summary
- SpiceDB relationship snapshot
- MinIO object manifest

导出不包含成员个人记忆；个人记忆只存在于成员本地 Hermes profile。

Go 服务端组织导出：

```bash
curl -sS -X POST "$TEAM_CLOUD_URL/v1/exports/org" \
  -H "Authorization: Bearer $TEAM_CLOUD_DASHBOARD_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"org_id":"hermes-labs"}'
```

返回值中 `personal_count` 必须为 `0`；这是兼容历史导出字段的固定值。

### 删除和保留

Team Cloud Go 不再接受 `deletion_scope=personal_memory`；成员个人记忆文件不在 Team Cloud 内，成员如需删除个人记忆，应在本地 Hermes profile 中处理。团队记忆的停用和硬删除通过 Dashboard “记忆治理”或 `POST /v1/memory/{id}/disable`、`DELETE /v1/memory/{id}` 执行，并写入审计事件。

retention policies 控制团队 memory、team soul backup、audit 和 export 的保留周期。

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

## 历史数据导入策略

Go Team Cloud 是首次上线目标，不提供旧 Python `team_cloud` 的 SessionDB 或历史记忆 provider 导入脚本。成员个人记忆和本地人格保留在各自 Hermes profile 中，通过 `/cloud-backup memory|soul` 做 MinIO/S3 备份和恢复；Team Cloud 只管理团队记忆、团队父人格和团队级备份。

如未来需要从外部历史系统迁入团队记忆，应作为新的导入专题实现，要求先完成 identity mapping、duplicate/conflict review、PII/secret scan、isolation smoke 和 cutover 前备份；该专题不属于当前 GA 首次上线路径。

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
- 可选团队记忆对象存储 bucket/manifest。
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
- 个人记忆不召回：检查本地 Hermes profile、`memories/` 文件和本地 memory 配置；Team Cloud 不召回个人记忆。
- 团队记忆不召回：检查 review 状态、team_id/project_id、SpiceDB read_team。
- CLI 显式新增团队记忆后 Dashboard 不显示：先确认 `/team status` 为 `mode: team`，再确认 agent 工具面包含 `team_memory_add`；如果走的是本地 `memory` 工具，说明 Team Cloud memory provider 未挂载或本轮 system prompt 未刷新。
- 普通对话没有自动出现在 Dashboard：当前 Go 服务端只自动保存 observation，不内置常驻 extraction worker；需要显式 `team_memory_add` 或后续抽取任务生成 memory item。
- 团队备份失败：检查团队 backup policy、encryption key、可选对象存储 manifest 和 backup job。
- CLI 本地备份失败：检查 `/cloud-backup status`、MinIO/S3 endpoint、bucket、root prefix、resource prefix 和 access/secret env key。
- 外部历史系统导入失败：按独立导入专题的 identity mapping、冲突检查和审计记录排查；当前 GA 首次上线不内置 legacy 导入脚本。

### Post-GA backlog

当前 Post-GA backlog 均为 non-blocking：

- `helm_runtime_lint_ci`
- `advanced_admin_analytics`
- `memory_quality_iteration`
- `external_audit_packet`

这些项目不阻塞 GA，可按运营优先级排期。

## 附录：关键命令

```bash
cd team_cloud && go test ./...
cd team_cloud && go vet ./...
cd team_cloud/dashboard && npm test -- --run
cd team_cloud/dashboard && npm run type-check
scripts/team-cloud-foundation-smoke.sh
scripts/team-cloud-isolation-smoke.sh
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
