# 2026-05-24 Dashboard Token Redesign 工作日志

## 工作内容

- 复查旧实现中 `TEAM_CLOUD_SERVICE_TOKEN`、`PUT /v1/bootstrap/runtime-config`、Dashboard 连接配置表单和 HMAC dashboard token 的使用点。
- 按 TDD 先更新测试，确认旧行为红灯：
  - 初始化创建不带 Authorization。
  - runtime-config endpoint 返回 404。
  - 登录 token 不再是 `hermes-dashboard-v1.*`。
  - 缺失或随机 Bearer token 访问受保护 API 返回 401。
  - K8S manifest 不再包含 `TEAM_CLOUD_SERVICE_TOKEN`，并包含 Redis session 配置。
- 后端改造：
  - 新增 Redis / memory session store。
  - 登录签发 `hcs_...` opaque token。
  - 移除 service token 鉴权路径和 runtime config overlay。
  - readiness/bootstrap status 增加 session store 检查。
- Dashboard 改造：
  - 删除 Service token、PostgreSQL、MinIO 连接配置表单。
  - 改为四步初始化向导。
  - 用 Vega Dark 风格重写全局样式。
- 部署改造：
  - Kubernetes manifest 增加 Redis Service/StatefulSet。
  - Team Cloud Go Deployment 通过 env/Secret 注入 Redis 配置。
  - Redis StatefulSet 覆盖默认 entrypoint，直接启动 `redis-server`，避免 minikube PVC 上的 `chown .: Operation not permitted` 导致 Redis CrashLoopBackOff。

## 验证记录

- `cd team_cloud && go test ./...`
- `cd team_cloud && go vet ./...`
- `cd team_cloud && go build ./...`
- `cd team_cloud/dashboard && npm test -- --run src/lib/teamCloudClient.test.ts src/app/page.test.tsx`
- `cd team_cloud/dashboard && npm run type-check`
- `cd team_cloud/dashboard && npm run build`

## 当前状态

代码侧已经达到本轮 GA 要求；minikube 环境已基于最新镜像重建，供 Dashboard 验收。

## minikube 重建记录

- 删除并重建 `hermes-team-cloud` namespace，清理旧 Pod、旧 PVC 和旧运行状态。
- 删除 minikube Docker 中旧 `hermes-team-cloud-go:minikube` 镜像。
- 重新部署 PostgreSQL + pgvector、SpiceDB、MinIO 和 Redis。
- 本地重建脚本增加 PostgreSQL `POSTGRES_DB` ready wait 和 MinIO alias retry，避免 StatefulSet Running 早于服务初始化完成时出现一次性失败。
- 重新构建并部署 `hermes-team-cloud-go:minikube`，镜像 ID 为 `sha256:f9ed92a444bf8c717b38738c5b4be055d30fd3ccd540bbfa39498bd0af948ac0`。
- 删除旧 `ghcr.io/hermes-agent/team-cloud-go:0.1.0` ReplicaSet，当前运行 Pod 只使用 `hermes-team-cloud-go:minikube`。
- 使用 `screen` 持有本地 `kubectl port-forward`，验收入口为 `http://127.0.0.1:8780/dashboard/`。

## minikube 冒烟记录

- `kubectl get pods -n hermes-team-cloud`：Team Cloud Go 2/2、PostgreSQL、Redis、MinIO、SpiceDB 均为 `Running`。
- `GET /healthz`：返回 `status=ok`。
- `GET /readyz`：返回 `status=ready`，`backend/authz/backup_object_store/config/session_store` 均为 `true`。
- `GET /v1/bootstrap/status`：返回 `initialized=false`，且 `postgres_configured/redis_configured/minio_configured/dashboard/session_store` 均为 `true`。
- `HEAD /dashboard/`：返回 `200 OK`。

## 二次清理重建记录

- 2026-05-24 再次复查新增需求后，确认代码和文档口径已覆盖无 service token 初始化、Redis session token、Step-by-Step 初始化页和 Vega Dark Dashboard。
- 重新执行 `go test ./...`、`go vet ./...`、`go build ./...`、Dashboard vitest、`npm run type-check`、`npm run build` 和 `git diff --check -- team_cloud teamDoc`。
- 停止旧本地转发，删除并重建 `hermes-team-cloud` namespace，删除旧 `hermes-team-cloud-go:minikube` 镜像。
- 基于当前源码重新执行 `minikube image build -t hermes-team-cloud-go:minikube .`，镜像 ID 仍为内容一致的 `sha256:f9ed92a444bf8c717b38738c5b4be055d30fd3ccd540bbfa39498bd0af948ac0`。
- 重新部署 PostgreSQL、SpiceDB、MinIO、Redis 和 Team Cloud Go；当前 Pod 均为 `Running`，Team Cloud Go 2 个副本均使用 `hermes-team-cloud-go:minikube`。
- 使用 `screen` 持有 `kubectl port-forward`，验收入口继续为 `http://127.0.0.1:8780/dashboard/`。

## 初始化数据清理记录

- 2026-05-24 排查 Dashboard 最后一步返回 `already_initialized`，确认旧环境曾返回 `initialized=true`、`organization_count=1`、旧 `team_count=1`、`super_admin_count=1`；随后 GTC-65 已退役 `team_count` 和默认工作组。
- 停止旧 `screen` 端口转发，删除 `hermes-team-cloud` namespace，显式清理旧 PV 和 minikube hostpath 数据目录 `/tmp/hostpath-provisioner/hermes-team-cloud`。
- 删除并重建 `hermes-team-cloud-go:minikube` 镜像。
- 重新部署 PostgreSQL、SpiceDB、MinIO、Redis 和 Team Cloud Go，重新创建 pgvector extension 和 `hermes-personal-backups` bucket。
- 清理后 `/v1/bootstrap/status` 返回 `initialized=false`，`organization_count/super_admin_count` 均为 `0`。
