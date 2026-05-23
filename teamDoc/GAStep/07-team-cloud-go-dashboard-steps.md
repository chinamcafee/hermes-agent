# Team Cloud Go Dashboard 一体化实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 在 `team_cloud_go/` 内交付随 Go 服务一体部署的 React + Next.js 静态管理台，并补齐首次初始化、超级管理员创建、组织/团队/成员、权限、记忆治理、备份、审计和 minikube 本地 Kubernetes 部署文档。

**架构：** Dashboard 是 `team_cloud_go/dashboard/` 下的独立 Next.js TypeScript 静态导出应用，构建产物由 Go 服务在 `/dashboard/` 托管。管理 API 和 bootstrap API 由同一个 Go 服务提供，Hermes 本地 dashboard/CLI 只负责本地个人事务和 Team Cloud 远程地址/token 配置。

**技术栈：** Go 1.24 `net/http`、Next.js static export、React、TypeScript、Vitest、Docker multi-stage、Kubernetes YAML、PostgreSQL/pgvector、SpiceDB/Authzed compatible HTTP、MinIO/S3。

---

## 文件结构

- 创建：`team_cloud_go/dashboard/`，包含 Next.js App Router 静态导出、Dashboard client、组件、样式和 Vitest 测试。
- 修改：`team_cloud_go/internal/config/config.go`，新增 Dashboard 静态目录和开关。
- 修改：`team_cloud_go/internal/httpapi/server.go`，新增 `/dashboard/` 静态托管和 `/v1/bootstrap/*` API。
- 修改：`team_cloud_go/internal/httpapi/*_test.go`，覆盖静态托管、bootstrap 状态和 super-admin 创建。
- 修改：`team_cloud_go/Dockerfile`、`team_cloud_go/deploy/kubernetes/team-cloud-go.yaml`、`team_cloud_go/internal/deploy/deploy_test.go`，将 Dashboard 构建产物纳入镜像和部署。
- 修改：`team_cloud_go/README.md` 和 `teamDoc` 设计、backlog、验收、release manual。
- 创建：`teamDoc/releaseManual/team-cloud-go-minikube-dashboard-manual.md`。

## 工作包

| ID | 工作包 | 主要产出 | 前置 | 状态 |
| --- | --- | --- | --- | --- |
| GTC-30 | Dashboard 职责边界冻结 | 设计、步骤、进度和日志落盘 | GTC-29 | In Progress |
| GTC-31 | Go Dashboard 静态托管 TDD | `/dashboard/`、asset、SPA fallback 测试 | GTC-30 | Not Started |
| GTC-32 | Bootstrap API TDD | `GET /v1/bootstrap/status`、`POST /v1/bootstrap/super-admin` 测试 | GTC-31 | Not Started |
| GTC-33 | Go 服务实现 | Dashboard config、静态托管、bootstrap API、审计和 owner relationship | GTC-32 | Not Started |
| GTC-34 | Next.js Dashboard scaffold | package、Next config、TypeScript、测试和 build 脚本 | GTC-33 | Not Started |
| GTC-35 | Dashboard 管理页面 | 初始化向导、概览、组织/团队/成员、权限、记忆 review、备份、审计 | GTC-34 | Not Started |
| GTC-36 | 镜像和 Kubernetes 一体部署 | Docker multi-stage、Dashboard env、manifest 和 deploy 测试 | GTC-35 | Not Started |
| GTC-37 | 文档和 release manual | `teamDoc`、Go README、release manual、minikube 手册 | GTC-36 | Not Started |
| GTC-38 | GA 复核验证 | Go、Dashboard、build、manifest、diff 和文档一致性验证 | GTC-37 | Not Started |

## 任务明细

### GTC-30：Dashboard 职责边界冻结

**文件：**
- 创建：`teamDoc/GAStep/07-team-cloud-go-dashboard-steps.md`
- 修改：`teamDoc/GAStep/progress-tracker.md`
- 创建：`teamDoc/GALog/2026-05-23-team-cloud-go-dashboard.md`

- [ ] **步骤 1：写入计划和进度**

将 GTC-30 到 GTC-38 加入进度追踪，初始只将 GTC-30 标记 `In Progress`。

- [ ] **步骤 2：记录架构边界**

日志中记录：Team Cloud 管理台属于 `team_cloud_go/dashboard/`，本地 Hermes dashboard/CLI 不承载团队云端管理页面。

- [ ] **步骤 3：进度更新**

完成计划和日志后把 GTC-30 标为 `Done`。

### GTC-31：Go Dashboard 静态托管 TDD

**文件：**
- 创建：`team_cloud_go/internal/httpapi/dashboard_test.go`
- 修改：`team_cloud_go/internal/httpapi/server.go`
- 修改：`team_cloud_go/internal/config/config.go`

- [ ] **步骤 1：编写失败测试**

新增测试覆盖 `/dashboard` 重定向、`/dashboard/` 返回 HTML、`/dashboard/assets/app.js` 返回静态资源、`/dashboard/settings` 回退到 `index.html`。

- [ ] **步骤 2：运行测试验证失败**

运行：`cd team_cloud_go && go test ./internal/httpapi -run 'TestDashboardStatic' -count=1`
预期：FAIL，原因是路由未注册或配置字段不存在。

- [ ] **步骤 3：实现静态托管**

新增 `Config.DashboardEnabled`、`Config.DashboardDir`，在 `routes()` 注册 `/dashboard` 和 `/dashboard/`。静态 handler 只托管文件，不绕过任何 `/api` 或 `/v1` 鉴权。

- [ ] **步骤 4：运行测试验证通过**

运行：`cd team_cloud_go && go test ./internal/httpapi -run 'TestDashboardStatic' -count=1`
预期：PASS。

### GTC-32：Bootstrap API TDD

**文件：**
- 创建：`team_cloud_go/internal/httpapi/bootstrap_test.go`
- 修改：`team_cloud_go/internal/httpapi/server.go`

- [ ] **步骤 1：编写失败测试**

测试 `GET /v1/bootstrap/status` 无需 token 可返回 service、version、initialized、organization_count、owner_count、checks。测试 `POST /v1/bootstrap/super-admin` 必须带 service token，创建 org、owner member 和 organization owner relationship，并在二次调用时返回 409。

- [ ] **步骤 2：运行测试验证失败**

运行：`cd team_cloud_go && go test ./internal/httpapi -run 'TestBootstrap' -count=1`
预期：FAIL，原因是 bootstrap 路由未实现。

- [ ] **步骤 3：实现 bootstrap**

`status` 使用 backend readiness、authz readiness、object store readiness 和 owner member 计数判断初始化状态。`super-admin` 使用 service token 创建组织、owner 成员、organization owner relationship 和 audit event。

- [ ] **步骤 4：运行测试验证通过**

运行：`cd team_cloud_go && go test ./internal/httpapi -run 'TestBootstrap' -count=1`
预期：PASS。

### GTC-33：Go 服务实现收口

**文件：**
- 修改：`team_cloud_go/internal/config/config.go`
- 修改：`team_cloud_go/internal/httpapi/server.go`
- 修改：`team_cloud_go/internal/httpapi/server_test.go`

- [ ] **步骤 1：运行相关 Go 测试**

运行：`cd team_cloud_go && go test ./internal/httpapi -count=1`
预期：PASS。

- [ ] **步骤 2：补齐错误语义**

确认 bootstrap 重复初始化返回 `409 Conflict`，缺失 token 返回 `401 Unauthorized`，payload 缺少 org/member 字段返回 `400 Bad Request`。

- [ ] **步骤 3：记录进度**

更新 `progress-tracker.md` 中 GTC-31 到 GTC-33 的状态和证据。

### GTC-34：Next.js Dashboard scaffold

**文件：**
- 创建：`team_cloud_go/dashboard/package.json`
- 创建：`team_cloud_go/dashboard/package-lock.json`
- 创建：`team_cloud_go/dashboard/next.config.mjs`
- 创建：`team_cloud_go/dashboard/tsconfig.json`
- 创建：`team_cloud_go/dashboard/src/app/layout.tsx`
- 创建：`team_cloud_go/dashboard/src/app/page.tsx`
- 创建：`team_cloud_go/dashboard/src/app/globals.css`
- 创建：`team_cloud_go/dashboard/src/lib/teamCloudClient.ts`
- 创建：`team_cloud_go/dashboard/src/**/*.test.ts(x)`

- [ ] **步骤 1：写 UI 测试**

Vitest 覆盖初始化向导、连接设置、管理页标签、主要 API action payload。

- [ ] **步骤 2：运行测试验证失败**

运行：`cd team_cloud_go/dashboard && npm test -- --run`
预期：FAIL，原因是组件和 client 尚不存在。

- [ ] **步骤 3：实现静态 Dashboard scaffold**

创建 App Router 单页管理台，使用 `output: 'export'` 和相对 API URL；token 默认存入 `sessionStorage`。

- [ ] **步骤 4：运行测试和类型检查**

运行：`cd team_cloud_go/dashboard && npm test -- --run && npm run type-check`
预期：PASS。

### GTC-35：Dashboard 管理页面

**文件：**
- 修改：`team_cloud_go/dashboard/src/app/page.tsx`
- 修改：`team_cloud_go/dashboard/src/app/globals.css`
- 修改：`team_cloud_go/dashboard/src/lib/teamCloudClient.ts`

- [ ] **步骤 1：实现功能页面**

页面包含：首次初始化、服务状态、组织/团队/成员、权限关系写入与检查、记忆 review、个人备份策略与运行、审计查询、Hermes 本地连接配置提示。

- [ ] **步骤 2：运行 Dashboard 验证**

运行：`cd team_cloud_go/dashboard && npm test -- --run && npm run build`
预期：PASS，且生成 `out/index.html`。

- [ ] **步骤 3：更新进度**

把 GTC-34 和 GTC-35 标记完成并写 GALog。

### GTC-36：镜像和 Kubernetes 一体部署

**文件：**
- 修改：`team_cloud_go/Dockerfile`
- 修改：`team_cloud_go/deploy/kubernetes/team-cloud-go.yaml`
- 修改：`team_cloud_go/internal/deploy/deploy_test.go`

- [ ] **步骤 1：编写 deploy 失败测试**

测试 Dockerfile 包含 Node dashboard build stage、`npm ci`、`npm run build`、最终镜像复制 `/usr/share/team-cloud-go/dashboard`。测试 K8s manifest 注入 `TEAM_CLOUD_DASHBOARD_DIR`。

- [ ] **步骤 2：运行测试验证失败**

运行：`cd team_cloud_go && go test ./internal/deploy -count=1`
预期：FAIL。

- [ ] **步骤 3：实现 Docker/K8s 变更**

Dockerfile 增加 Node 22 Alpine dashboard stage，最终 distroless 镜像携带静态 `out/`。Kubernetes manifest 设置 Dashboard 目录和可选开关。

- [ ] **步骤 4：运行 deploy 测试**

运行：`cd team_cloud_go && go test ./internal/deploy -count=1`
预期：PASS。

### GTC-37：文档和 release manual

**文件：**
- 修改：`teamDoc/README.md`
- 修改：`teamDoc/03-target-architecture.md`
- 修改：`teamDoc/10-implementation-backlog.md`
- 修改：`teamDoc/12-ga-product-requirements.md`
- 修改：`teamDoc/16-ga-test-release-checklist.md`
- 修改：`teamDoc/17-team-cloud-go-service-design.md`
- 修改：`team_cloud_go/README.md`
- 修改：`teamDoc/releaseManual/team-cloud-ga-release-manual.md`
- 创建：`teamDoc/releaseManual/team-cloud-go-minikube-dashboard-manual.md`
- 创建：`teamDoc/GADoc/GTC-30-38-team-cloud-go-dashboard-ga.md`

- [ ] **步骤 1：更新职责边界文档**

明确 Team Cloud admin UI 属于 `team_cloud_go/dashboard/`，Hermes 本地 dashboard/CLI 只配置远程地址和本地个人事务。

- [ ] **步骤 2：编写 minikube 手册**

覆盖 minikube、PostgreSQL/pgvector、SpiceDB、MinIO、Team Cloud Go + Dashboard、本地 Hermes dashboard/CLI 编译和连接步骤。

- [ ] **步骤 3：更新 release manual**

替换旧 Web shell 口径，加入 `/dashboard/`、bootstrap API、service token 初始化和 Go Dashboard 部署证据。

### GTC-38：GA 复核验证

**文件：**
- 修改：`teamDoc/GAStep/progress-tracker.md`
- 修改：`teamDoc/GALog/2026-05-23-team-cloud-go-dashboard.md`
- 修改：`teamDoc/GADoc/GTC-30-38-team-cloud-go-dashboard-ga.md`

- [ ] **步骤 1：运行 Go 验证**

运行：`cd team_cloud_go && go test ./... && go vet ./... && go build ./cmd/team-cloud-server`

- [ ] **步骤 2：运行 Dashboard 验证**

运行：`cd team_cloud_go/dashboard && npm test -- --run && npm run type-check && npm run build`

- [ ] **步骤 3：运行部署和文档一致性验证**

运行：`ruby -e 'require "yaml"; YAML.load_stream(File.read("team_cloud_go/deploy/kubernetes/team-cloud-go.yaml")); puts "ok"'`

运行：`git diff --check -- team_cloud_go teamDoc`

运行：`rg -n "Web shell|web shell" teamDoc team_cloud_go`

- [ ] **步骤 4：GA 收口**

如果验证全部通过，把 GTC-36 到 GTC-38 标记 `Done`，在 GADoc 写入最终证据。
