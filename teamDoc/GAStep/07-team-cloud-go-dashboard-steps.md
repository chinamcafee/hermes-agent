# Team Cloud Go Dashboard 一体化实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [x]`）语法来跟踪进度。

**目标：** 在 `team_cloud/` 内交付随 Go 服务一体部署的 React + Next.js 静态管理台，并补齐首次初始化、超级管理员创建、组织/团队/成员、权限、记忆治理、备份、审计和 minikube 本地 Kubernetes 部署文档。

**架构：** Dashboard 是 `team_cloud/dashboard/` 下的独立 Next.js TypeScript 静态导出应用，构建产物由 Go 服务在 `/dashboard/` 托管。管理 API 和 bootstrap API 由同一个 Go 服务提供，Hermes 本地 dashboard/CLI 只负责本地个人事务和 Team Cloud 远程地址/token 配置。

**技术栈：** Go 1.24 `net/http`、Next.js static export、React、TypeScript、Vitest、Docker multi-stage、Kubernetes YAML、PostgreSQL/pgvector、SpiceDB/Authzed compatible HTTP、MinIO/S3。

---

## 文件结构

- 创建：`team_cloud/dashboard/`，包含 Next.js App Router 静态导出、Dashboard client、组件、样式和 Vitest 测试。
- 修改：`team_cloud/internal/config/config.go`，新增 Dashboard 静态目录和开关。
- 修改：`team_cloud/internal/httpapi/server.go`，新增 `/dashboard/` 静态托管和 `/v1/bootstrap/*` API。
- 修改：`team_cloud/internal/httpapi/*_test.go`，覆盖静态托管、bootstrap 状态和 super-admin 创建。
- 修改：`team_cloud/Dockerfile`、`team_cloud/deploy/kubernetes/team-cloud-go.yaml`、`team_cloud/internal/deploy/deploy_test.go`，将 Dashboard 构建产物纳入镜像和部署。
- 修改：`team_cloud/README.md` 和 `teamDoc` 设计、backlog、验收、release manual。
- 创建：`teamDoc/releaseManual/team-cloud-go-minikube-dashboard-manual.md`。

## 工作包

| ID | 工作包 | 主要产出 | 前置 | 状态 |
| --- | --- | --- | --- | --- |
| GTC-30 | Dashboard 职责边界冻结 | 设计、步骤、进度和日志落盘 | GTC-29 | Done |
| GTC-31 | Go Dashboard 静态托管 TDD | `/dashboard/`、asset、SPA fallback 测试 | GTC-30 | Done |
| GTC-32 | Bootstrap API TDD | `GET /v1/bootstrap/status`、`POST /v1/bootstrap/super-admin` 测试 | GTC-31 | Done |
| GTC-33 | Go 服务实现 | Dashboard config、静态托管、bootstrap API、审计和 owner relationship | GTC-32 | Done |
| GTC-34 | Next.js Dashboard scaffold | package、Next config、TypeScript、测试和 build 脚本 | GTC-33 | Done |
| GTC-35 | Dashboard 管理页面 | 初始化向导、概览、组织/团队/成员、权限、记忆 review、备份、审计 | GTC-34 | Done |
| GTC-36 | 镜像和 Kubernetes 一体部署 | Docker multi-stage、Dashboard env、manifest 和 deploy 测试 | GTC-35 | Done |
| GTC-37 | 文档和 release manual | `teamDoc`、Go README、release manual、minikube 手册 | GTC-36 | Done |
| GTC-38 | GA 复核验证 | Go、Dashboard、build、manifest、diff 和文档一致性验证 | GTC-37 | Done |
| GTC-39 | minikube StorageClass runbook 修复 | storage addon、PVC storageClass 和 Pending 排障文档 | GTC-38 | Done |
| GTC-40 | minikube MinIO client 命令修复 | `kubectl run --command` bucket 初始化命令和验证文档 | GTC-39 | Done |
| GTC-41 | minikube image build runbook 修复 | 默认单节点 image build 和多 Ready 节点 `--all` 条件说明 | GTC-40 | Done |
| GTC-42 | Kubernetes nonroot UID 部署修复 | manifest UID/GID、部署测试和 CreateContainerConfigError 排障 | GTC-41 | Done |

## 任务明细

### GTC-30：Dashboard 职责边界冻结

**文件：**
- 创建：`teamDoc/GAStep/07-team-cloud-go-dashboard-steps.md`
- 修改：`teamDoc/GAStep/progress-tracker.md`
- 创建：`teamDoc/GALog/2026-05-23-team-cloud-go-dashboard.md`

- [x] **步骤 1：写入计划和进度**

将 GTC-30 到 GTC-38 加入进度追踪，初始只将 GTC-30 标记 `In Progress`。

- [x] **步骤 2：记录架构边界**

日志中记录：Team Cloud 管理台属于 `team_cloud/dashboard/`，本地 Hermes dashboard/CLI/Desktop 不承载团队云端管理页面；Desktop 只通过 Hermes Agent Bridge 接入 Team Cloud。

- [x] **步骤 3：进度更新**

完成计划和日志后把 GTC-30 标为 `Done`。

### GTC-31：Go Dashboard 静态托管 TDD

**文件：**
- 创建：`team_cloud/internal/httpapi/dashboard_test.go`
- 修改：`team_cloud/internal/httpapi/server.go`
- 修改：`team_cloud/internal/config/config.go`

- [x] **步骤 1：编写失败测试**

新增测试覆盖 `/dashboard` 重定向、`/dashboard/` 返回 HTML、`/dashboard/assets/app.js` 返回静态资源、`/dashboard/settings` 回退到 `index.html`。

- [x] **步骤 2：运行测试验证失败**

运行：`cd team_cloud && go test ./internal/httpapi -run 'TestDashboardStatic' -count=1`
预期：FAIL，原因是路由未注册或配置字段不存在。

- [x] **步骤 3：实现静态托管**

新增 `Config.DashboardEnabled`、`Config.DashboardDir`，在 `routes()` 注册 `/dashboard` 和 `/dashboard/`。静态 handler 只托管文件，不绕过任何 `/api` 或 `/v1` 鉴权。

- [x] **步骤 4：运行测试验证通过**

运行：`cd team_cloud && go test ./internal/httpapi -run 'TestDashboardStatic' -count=1`
预期：PASS。

### GTC-32：Bootstrap API TDD

**文件：**
- 创建：`team_cloud/internal/httpapi/bootstrap_test.go`
- 修改：`team_cloud/internal/httpapi/server.go`

- [x] **步骤 1：编写失败测试**

测试 `GET /v1/bootstrap/status` 无需 token 可返回 service、version、initialized、organization_count、owner_count、checks。2026-05-24 起，`POST /v1/bootstrap/super-admin` 在未初始化状态无需 service token，创建 org、owner member 和 organization owner relationship，并在二次调用时返回 409。

- [x] **步骤 2：运行测试验证失败**

运行：`cd team_cloud && go test ./internal/httpapi -run 'TestBootstrap' -count=1`
预期：FAIL，原因是 bootstrap 路由未实现。

- [x] **步骤 3：实现 bootstrap**

`status` 使用 backend readiness、authz readiness、session store、object store readiness 和 owner member 计数判断初始化状态。`super-admin` 在首次初始化窗口创建组织、owner 成员、organization owner relationship 和 audit event。

- [x] **步骤 4：运行测试验证通过**

运行：`cd team_cloud && go test ./internal/httpapi -run 'TestBootstrap' -count=1`
预期：PASS。

### GTC-33：Go 服务实现收口

**文件：**
- 修改：`team_cloud/internal/config/config.go`
- 修改：`team_cloud/internal/httpapi/server.go`
- 修改：`team_cloud/internal/httpapi/server_test.go`

- [x] **步骤 1：运行相关 Go 测试**

运行：`cd team_cloud && go test ./internal/httpapi -count=1`
预期：PASS。

- [x] **步骤 2：补齐错误语义**

确认 bootstrap 重复初始化返回 `409 Conflict`，缺失 token 返回 `401 Unauthorized`，payload 缺少 org/member 字段返回 `400 Bad Request`。

- [x] **步骤 3：记录进度**

更新 `progress-tracker.md` 中 GTC-31 到 GTC-33 的状态和证据。

### GTC-34：Next.js Dashboard scaffold

**文件：**
- 创建：`team_cloud/dashboard/package.json`
- 创建：`team_cloud/dashboard/package-lock.json`
- 创建：`team_cloud/dashboard/next.config.mjs`
- 创建：`team_cloud/dashboard/tsconfig.json`
- 创建：`team_cloud/dashboard/src/app/layout.tsx`
- 创建：`team_cloud/dashboard/src/app/page.tsx`
- 创建：`team_cloud/dashboard/src/app/globals.css`
- 创建：`team_cloud/dashboard/src/lib/teamCloudClient.ts`
- 创建：`team_cloud/dashboard/src/**/*.test.ts(x)`

- [x] **步骤 1：写 UI 测试**

Vitest 覆盖初始化向导、连接设置、管理页标签、主要 API action payload。

- [x] **步骤 2：运行测试验证失败**

运行：`cd team_cloud/dashboard && npm test -- --run`
预期：FAIL，原因是组件和 client 尚不存在。

- [x] **步骤 3：实现静态 Dashboard scaffold**

创建 App Router 单页管理台，使用 `output: 'export'` 和相对 API URL；token 默认存入 `sessionStorage`。

- [x] **步骤 4：运行测试和类型检查**

运行：`cd team_cloud/dashboard && npm test -- --run && npm run type-check`
预期：PASS。

### GTC-35：Dashboard 管理页面

**文件：**
- 修改：`team_cloud/dashboard/src/app/page.tsx`
- 修改：`team_cloud/dashboard/src/app/globals.css`
- 修改：`team_cloud/dashboard/src/lib/teamCloudClient.ts`

- [x] **步骤 1：实现功能页面**

页面包含：首次初始化、服务状态、团队成员、只读角色权限说明、记忆治理、团队记忆备份管理、审计查询、Hermes 本地连接配置提示。

- [x] **步骤 2：运行 Dashboard 验证**

运行：`cd team_cloud/dashboard && npm test -- --run && npm run build`
预期：PASS，且生成 `out/index.html`。

- [x] **步骤 3：更新进度**

把 GTC-34 和 GTC-35 标记完成并写 GALog。

### GTC-36：镜像和 Kubernetes 一体部署

**文件：**
- 修改：`team_cloud/Dockerfile`
- 修改：`team_cloud/deploy/kubernetes/team-cloud-go.yaml`
- 修改：`team_cloud/internal/deploy/deploy_test.go`

- [x] **步骤 1：编写 deploy 失败测试**

测试 Dockerfile 包含 Node dashboard build stage、`npm ci`、`npm run build`、最终镜像复制 `/usr/share/team-cloud-go/dashboard`。测试 K8s manifest 注入 `TEAM_CLOUD_DASHBOARD_DIR`。

- [x] **步骤 2：运行测试验证失败**

运行：`cd team_cloud && go test ./internal/deploy -count=1`
预期：FAIL。

- [x] **步骤 3：实现 Docker/K8s 变更**

Dockerfile 增加 Node 22 Alpine dashboard stage，最终 distroless 镜像携带静态 `out/`。Kubernetes manifest 设置 Dashboard 目录和可选开关。

- [x] **步骤 4：运行 deploy 测试**

运行：`cd team_cloud && go test ./internal/deploy -count=1`
预期：PASS。

### GTC-37：文档和 release manual

**文件：**
- 修改：`teamDoc/README.md`
- 修改：`teamDoc/03-target-architecture.md`
- 修改：`teamDoc/10-implementation-backlog.md`
- 修改：`teamDoc/12-ga-product-requirements.md`
- 修改：`teamDoc/16-ga-test-release-checklist.md`
- 修改：`teamDoc/17-team-cloud-go-service-design.md`
- 修改：`team_cloud/README.md`
- 修改：`teamDoc/releaseManual/team-cloud-ga-release-manual.md`
- 创建：`teamDoc/releaseManual/team-cloud-go-minikube-dashboard-manual.md`
- 创建：`teamDoc/GADoc/GTC-30-38-team-cloud-go-dashboard-ga.md`

- [x] **步骤 1：更新职责边界文档**

明确 Team Cloud admin UI 属于 `team_cloud/dashboard/`，Hermes 本地 dashboard/CLI 只配置远程地址和本地个人事务。

- [x] **步骤 2：编写 minikube 手册**

覆盖 minikube、PostgreSQL/pgvector、SpiceDB、MinIO、Team Cloud Go + Dashboard、本地 Hermes dashboard/CLI 编译和连接步骤。

- [x] **步骤 3：更新 release manual**

替换旧 Web shell 口径，加入 `/dashboard/`、bootstrap API、无 service token 初始化和 Go Dashboard 部署证据。

### GTC-38：GA 复核验证

**文件：**
- 修改：`teamDoc/GAStep/progress-tracker.md`
- 修改：`teamDoc/GALog/2026-05-23-team-cloud-go-dashboard.md`
- 修改：`teamDoc/GADoc/GTC-30-38-team-cloud-go-dashboard-ga.md`

- [x] **步骤 1：运行 Go 验证**

运行：`cd team_cloud && go test ./... && go vet ./... && go build ./cmd/team-cloud-server`

- [x] **步骤 2：运行 Dashboard 验证**

运行：`cd team_cloud/dashboard && npm test -- --run && npm run type-check && npm run build`

- [x] **步骤 3：运行部署和文档一致性验证**

运行：`ruby -e 'require "yaml"; YAML.load_stream(File.read("team_cloud/deploy/kubernetes/team-cloud-go.yaml")); puts "ok"'`

运行：`git diff --check -- team_cloud teamDoc`

运行：`rg -n "Web shell|web shell" teamDoc team_cloud`

- [x] **步骤 4：GA 收口**

如果验证全部通过，把 GTC-36 到 GTC-38 标记 `Done`，在 GADoc 写入最终证据。

### GTC-39：minikube StorageClass runbook 修复

**文件：**
- 修改：`teamDoc/releaseManual/team-cloud-go-minikube-dashboard-manual.md`
- 修改：`teamDoc/GAStep/progress-tracker.md`
- 创建：`teamDoc/GALog/2026-05-23-minikube-storageclass-fix.md`
- 创建：`teamDoc/GADoc/GTC-39-minikube-storageclass-runbook-fix.md`

- [x] **步骤 1：确认根因**

验证 `kubectl get storageclass` 曾缺失默认类，PVC 事件出现 `no persistent volumes available for this claim and no storage class is set`。

- [x] **步骤 2：补手册前置条件**

在 minikube 手册中加入 `storage-provisioner`、`default-storageclass` addon 启用和 `kubectl get storageclass` 验证。

- [x] **步骤 3：显式绑定 minikube storageClass**

PostgreSQL 和 MinIO 示例 PVC 模板新增 `storageClassName: standard`。

- [x] **步骤 4：补排障和验收证据**

新增 PVC Pending 排障步骤，并在 GALog/GADoc/progress-tracker 中记录已完成状态和验证证据。

### GTC-40：minikube MinIO client 命令修复

**文件：**
- 修改：`teamDoc/releaseManual/team-cloud-go-minikube-dashboard-manual.md`
- 修改：`teamDoc/GAStep/progress-tracker.md`
- 创建：`teamDoc/GALog/2026-05-23-minikube-minio-client-fix.md`
- 创建：`teamDoc/GADoc/GTC-40-minikube-minio-client-command-fix.md`

- [x] **步骤 1：复现命令失败**

原命令将 `sh` 传给 `mc` entrypoint，输出 `mc: <ERROR> sh is not a recognized command`。

- [x] **步骤 2：验证正确命令**

使用 `kubectl run ... --command -- sh -c ...` 成功创建 `local/hermes-personal-backups`。

- [x] **步骤 3：同步手册和进度**

更新 minikube 手册、GALog、GADoc 和 progress tracker。

### GTC-41：minikube image build runbook 修复

**文件：**
- 修改：`teamDoc/releaseManual/team-cloud-go-minikube-dashboard-manual.md`
- 修改：`teamDoc/GAStep/progress-tracker.md`
- 创建：`teamDoc/GALog/2026-05-23-minikube-image-build-fix.md`
- 创建：`teamDoc/GADoc/GTC-41-minikube-image-build-runbook-fix.md`

- [x] **步骤 1：确认失败模式**

`minikube image build --all` 在多节点 profile 中触发 worker 构建，worker DNS 解析 `proxy.golang.org` 超时。

- [x] **步骤 2：验证默认路径**

运行 `minikube image build -t hermes-team-cloud-go:minikube .` 成功，镜像写入 minikube image store。

- [x] **步骤 3：同步手册和进度**

默认命令改为不带 `--all`，多 Ready 节点场景保留 `--all` 可选说明，并更新 GALog/GADoc/progress tracker。

### GTC-42：Kubernetes nonroot UID 部署修复

**文件：**
- 修改：`team_cloud/deploy/kubernetes/team-cloud-go.yaml`
- 修改：`team_cloud/internal/deploy/deploy_test.go`
- 修改：`teamDoc/releaseManual/team-cloud-go-minikube-dashboard-manual.md`
- 修改：`teamDoc/GAStep/progress-tracker.md`
- 创建：`teamDoc/GALog/2026-05-23-kubernetes-nonroot-uid-fix.md`
- 创建：`teamDoc/GADoc/GTC-42-kubernetes-nonroot-uid-fix.md`

- [x] **步骤 1：复现部署错误**

新 Pod 进入 `CreateContainerConfigError`，事件显示 distroless `nonroot` 非数字用户名无法被 `runAsNonRoot` 验证。

- [x] **步骤 2：TDD 固化 manifest 要求**

部署测试新增 `runAsUser: 65532` 和 `runAsGroup: 65532` 断言，并先验证红灯。

- [x] **步骤 3：修复 manifest 和集群**

Deployment manifest 新增 UID/GID，集群中 patch 当前 Deployment 后 rollout 成功。

- [x] **步骤 4：验证服务连通性**

验证 `/readyz`、`/v1/bootstrap/status`、`/dashboard/` 和 `api/organizations`。
