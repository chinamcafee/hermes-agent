# Team Cloud Go Dashboard 一体化工作日志

日期：2026-05-23

## 背景

用户确认采用服务端职责收敛方案：团队协作、首次初始化、超级管理员、组织/团队/成员、权限、团队记忆治理、备份和审计管理均应属于云端 `team_cloud_go` 服务端。Hermes 本地 dashboard/CLI 保持 runtime 和个人本地事务边界，只负责配置 Team Cloud 远程地址、token 和本地个人环境。

## 本轮范围

- 在 `team_cloud_go/dashboard/` 新建 React + Next.js TypeScript 静态管理台。
- Go 服务在 `/dashboard/` 托管 Dashboard 构建产物。
- Go 服务新增 `/v1/bootstrap/status` 和 `/v1/bootstrap/super-admin`，支撑首次初始化向导和超级管理员创建。
- Dockerfile 使用 multi-stage 构建 Go 服务和 Dashboard，最终镜像一体部署到 Kubernetes。
- 更新 `teamDoc`、`team_cloud_go/README.md` 和 `teamDoc/releaseManual`。
- 新增 minikube 本地 Kubernetes 部署手册，覆盖 PostgreSQL/pgvector、SpiceDB、MinIO、Team Cloud Go + Dashboard 和本地 Hermes dashboard/CLI 连接。

## 执行记录

- GTC-30：新增 `07-team-cloud-go-dashboard-steps.md`，并在 `progress-tracker.md` 追加 GTC-30 到 GTC-38。
- GTC-31 红灯：新增 `internal/httpapi/dashboard_test.go`，运行 `go test ./internal/httpapi -run 'TestDashboardStatic|TestBootstrap' -count=1`，因 `Config.DashboardEnabled` 和 `Config.DashboardDir` 尚不存在而失败。
- GTC-32 红灯：同一测试命令覆盖 `/v1/bootstrap/status` 和 `/v1/bootstrap/super-admin`，当前尚未进入路由实现。
- GTC-36 红灯：扩展 `internal/deploy/deploy_test.go`，运行 `go test ./internal/deploy -count=1`，因 Dockerfile 缺少 `node:22-alpine AS dashboard-build` 阶段失败。
- GTC-31/GTC-32/GTC-33 绿灯：新增 `DashboardEnabled`、`DashboardDir`、`/dashboard/` 静态托管、SPA fallback、`/v1/bootstrap/status`、`/v1/bootstrap/super-admin` 和 owner relationship 初始化。运行 `go test ./internal/httpapi -count=1` 通过。
- GTC-34 红灯：新增 `team_cloud_go/dashboard` package、Vitest 配置和 Dashboard/client 测试。运行 `npm test -- --run`，因 `src/app/page.tsx` 和 `src/lib/teamCloudClient.ts` 尚不存在而失败。
- GTC-34/GTC-35 绿灯：实现 Next.js static export Dashboard、Team Cloud API client、初始化向导、组织/团队/成员、权限、记忆治理、备份、审计和本地连接视图。运行 `npm test -- --run`、`npm run type-check`、`npm run build` 通过。
- GTC-36 绿灯：Dockerfile 改为 Node 22 Dashboard build stage + Go build stage，最终 distroless 镜像复制 `/usr/share/team-cloud-go/dashboard`；Kubernetes manifest 注入 `TEAM_CLOUD_DASHBOARD_ENABLED` 和 `TEAM_CLOUD_DASHBOARD_DIR`。运行 `go test ./internal/deploy -count=1` 通过。
- GTC-37：更新 `teamDoc` 架构、Backlog、产品验收、发布检查清单、Go 服务设计、`team_cloud_go/README.md` 和 GA release manual；新增 minikube 本地 Kubernetes 部署手册。Dashboard npm audit 通过 `postcss` override 收敛到 0 vulnerabilities。
- GTC-38：完成新鲜验证。`go test ./...`、`go vet ./...`、`go build ./cmd/team-cloud-server`、`npm test -- --run`、`npm run type-check`、`npm run build`、`npm audit --audit-level=moderate`、Kubernetes YAML parse、`git diff --check -- team_cloud_go teamDoc`、release manual stale Web shell 扫描和 `docker build -t hermes-team-cloud-go:dashboard-ga team_cloud_go` 均通过。
