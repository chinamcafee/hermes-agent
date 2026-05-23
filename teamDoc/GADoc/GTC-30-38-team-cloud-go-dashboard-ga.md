# GTC-30 到 GTC-38 Team Cloud Go Dashboard GA 收口

日期：2026-05-23

## 范围

本轮新增需求将 Team Cloud 云端管理职责收敛到 `team_cloud_go`：

- `team_cloud_go/dashboard/` 新增 React + Next.js static export 管理台。
- Go 服务端在 `/dashboard/` 托管 Dashboard 静态产物，并提供 SPA fallback。
- Go 服务端新增 bootstrap status 和 super-admin 初始化 API。
- Dockerfile 和 Kubernetes manifest 一体化 Dashboard 部署。
- 文档、release manual 和 minikube 本地 Kubernetes 手册同步更新。

## 代码产出

| 产物 | 说明 |
| --- | --- |
| `team_cloud_go/internal/httpapi/dashboard.go` | `/dashboard` redirect、静态资源托管、SPA fallback 和禁用开关。 |
| `team_cloud_go/internal/httpapi/bootstrap.go` | `/v1/bootstrap/status`、`/v1/bootstrap/super-admin`、owner relationship 和 audit。 |
| `team_cloud_go/dashboard/` | Next.js Dashboard、Team Cloud client、Vitest 测试、static export 配置。 |
| `team_cloud_go/Dockerfile` | Node 22 Dashboard build stage + Go build stage + distroless runtime。 |
| `team_cloud_go/deploy/kubernetes/team-cloud-go.yaml` | Dashboard env 和静态目录注入。 |

## 职责边界

- Team Cloud Go Dashboard 负责首次初始化、超级管理员、组织/团队/成员、权限关系、记忆治理、个人备份和审计。
- 本地 Hermes dashboard/CLI 只负责本地 Agent runtime、个人本地环境和 Team Cloud 远程地址/token 配置。
- Python `team_cloud/` 仍为历史参考实现，不作为首次上线服务端。

## 验收证据

GTC-38 已完成以下新鲜验证：

- `cd team_cloud_go && go test ./...`：通过，覆盖 `internal/httpapi`、`internal/config`、`internal/deploy`、`internal/authz`、`internal/backup`、`internal/objectstore` 和 PostgreSQL schema/store 测试。
- `cd team_cloud_go && go vet ./...`：通过。
- `cd team_cloud_go && go build ./cmd/team-cloud-server`：通过。
- `cd team_cloud_go/dashboard && npm test -- --run`：2 个 test files、5 个 tests 通过。
- `cd team_cloud_go/dashboard && npm run type-check`：通过。
- `cd team_cloud_go/dashboard && npm run build`：通过，生成 static export，`out/index.html` 和 `out/_next` 存在。
- `cd team_cloud_go/dashboard && npm audit --audit-level=moderate`：0 vulnerabilities。
- `ruby -e 'require "yaml"; YAML.load_stream(File.read("team_cloud_go/deploy/kubernetes/team-cloud-go.yaml")); puts "ok"'`：通过。
- `git diff --check -- team_cloud_go teamDoc`：通过。
- `rg -n "Web shell|web shell" teamDoc/releaseManual teamDoc/17-team-cloud-go-service-design.md team_cloud_go/README.md`：无匹配，release manual 和 Go 设计已切换到 Team Cloud Go Dashboard 口径。
- `docker build -t hermes-team-cloud-go:dashboard-ga team_cloud_go`：通过，Node Dashboard stage、Go build stage 和 distroless runtime stage 均完成。

## 文档产出

- `teamDoc/releaseManual/team-cloud-ga-release-manual.md`
- `teamDoc/releaseManual/team-cloud-go-minikube-dashboard-manual.md`
- `team_cloud_go/README.md`
- `teamDoc/17-team-cloud-go-service-design.md`
