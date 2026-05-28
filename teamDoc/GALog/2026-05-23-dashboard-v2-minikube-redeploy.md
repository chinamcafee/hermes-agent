# Dashboard V2 minikube 重建部署记录

> 2026-05-24 更新：本日志中的 Service token 验收入口已被 GTC-60~64 取代。当前 Dashboard 首次初始化不需要 token；初始化后使用管理页帐号密码登录并获取 Redis session token。

日期：2026-05-23

## 复查结论

- Dashboard V2 后端、前端和文档已完成一致性复查。
- 复查中补齐成员查询、角色筛选、编辑基础资料、停用动作和本地连接复制按钮。
- 补齐后重新执行 Go、Dashboard、构建、安全和文档静态检查，均通过。

## 本地 Kubernetes 清理

- 删除并重建 `hermes-team-cloud` namespace，清理旧 Pod、旧容器和 PVC 数据。
- 删除 minikube Docker 中旧 `hermes-team-cloud-go:minikube` 镜像。
- 重新构建 `hermes-team-cloud-go:minikube`，新镜像 ID 为 `sha256:5438c1d2ffe8e89887d55222ffb4ff99804acd70803566909af33fa7ccb4adab`。

## 中间件和服务端

- 重新部署 PostgreSQL + pgvector，并执行 `create extension if not exists vector;`。
- 重新部署 SpiceDB 本地 memory datastore。
- 重新部署 MinIO，并创建 `hermes-personal-backups` bucket。
- 重新部署 Team Cloud Go + Dashboard，Deployment 使用 `hermes-team-cloud-go:minikube`。
- 删除旧的 0 副本 `ghcr.io/hermes-agent/team-cloud-go:0.1.0` ReplicaSet，避免验收时混淆。

## 冒烟验证

- `kubectl get pods -n hermes-team-cloud`：`hermes-team-cloud-go` 两个 Pod、`postgres-0`、`minio-0`、`spicedb` 均为 `Running`。
- `GET /healthz`：返回 `status=ok`。
- `GET /readyz`：返回 `status=ready`。
- `GET /v1/bootstrap/status`：返回 `initialized=false`，PostgreSQL、MinIO、backend、authz、dashboard 均 ready。
- `GET /dashboard/`：返回 `200 OK`，页面渲染独立 `Team Cloud 初始化引导`。

## 验收入口

- Dashboard: `http://localhost:8780/dashboard/`
- Service token: `dev-team-cloud-token`
- PostgreSQL DSN: `postgres://hermes:hermespass@postgres:5432/hermes_team_cloud?sslmode=disable`
- MinIO: `http://minio:9000`，bucket `hermes-personal-backups`，access key `minioadmin`，secret key `minioadmin123`

## 复查后第二次重建

- 按用户要求再次复查代码、文档、测试和集群状态。
- 新鲜验证命令：`go test ./...`、`go vet ./...`、`go build ./...`、`npm test -- --run`、`npm run type-check`、`npm run build`、`npm audit --audit-level=moderate`、`git diff --check -- team_cloud teamDoc` 均通过。
- 再次删除 `hermes-team-cloud` namespace，清理 Pod、PVC 和旧 `hermes-team-cloud-go:minikube` 镜像。
- 再次执行 `minikube image build -t hermes-team-cloud-go:minikube .`。源码未变化，最终镜像 digest 仍为 `sha256:5438c1d2ffe8e89887d55222ffb4ff99804acd70803566909af33fa7ccb4adab`。
- 再次部署 PostgreSQL + pgvector、SpiceDB、MinIO 和 Team Cloud Go。
- 冒烟检查：`/healthz` 返回 `ok`，`/readyz` 返回 `ready`，`/v1/bootstrap/status` 返回 `initialized=false` 且 PostgreSQL、MinIO、backend、authz、dashboard 均 ready，`/dashboard/` 返回 `200 OK` 并渲染独立初始化引导页。
