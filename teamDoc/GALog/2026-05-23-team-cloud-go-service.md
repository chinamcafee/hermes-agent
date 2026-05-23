# Team Cloud Go 服务端重写工作日志

日期：2026-05-23

## 背景

用户确认团队协作需要独立云端服务端承载团队记忆同步和成员管理 API，并要求在不修改 Python `team_cloud/` 的前提下，以 Go 技术栈在 `team_cloud_go/` 中重写服务端，便于 Kubernetes 部署。由于 Python 版从未上线，Go 版作为首次上线目标，允许破坏性更新。

## 已完成编码工作

- 新增独立 Go module：`team_cloud_go/go.mod`。
- 新增服务入口：`team_cloud_go/cmd/team-cloud-server/main.go`。
- 新增配置读取：`TEAM_CLOUD_SERVICE_TOKEN`、`TEAM_CLOUD_DATABASE_URL`、`TEAM_CLOUD_AUTO_MIGRATE`、`TEAM_CLOUD_BIND_ADDR`。
- 新增 HTTP API：
  - `/healthz`、`/readyz`、`/metrics`
  - `/api/organizations`
  - `/api/organizations/{org_id}/teams`
  - `/api/organizations/{org_id}/members`
  - `/api/organizations/{org_id}/members/invite`
  - `/api/organizations/{org_id}/members/{member_id}/disable`
  - `/v1/memory`
  - `/v1/memory/prefetch`
  - `/v1/memory/observations`
  - `/v1/memory/review`
  - `/v1/memory/review/{review_id}/approve`
  - `/v1/memory/review/{review_id}/reject`
  - `/v1/me/memory-backup-policy`
- 新增内存后端用于开发和单元测试。
- 新增 PostgreSQL 后端用于生产部署，并提供 `tcg_*` schema 和启动自动 migration。
- 新增 Dockerfile 和 Kubernetes all-in-one manifest。

## 测试记录

- 红灯：新增 config、postgres schema、deploy asset 测试后，`go test ./...` 失败于缺少 `DatabaseURL`、`AutoMigrate`、`SchemaSQL`、Dockerfile 和 Kubernetes manifest。
- 绿灯：完成实现后运行 `cd team_cloud_go && go test ./...`，全部包通过。
- 静态检查：已运行 `cd team_cloud_go && go vet ./...`，无输出，退出码为 0。
- 构建检查：已运行 `cd team_cloud_go && go build ./cmd/team-cloud-server`，退出码为 0；验证生成的本地二进制已删除。
- Manifest 检查：当前 Python 环境缺少 `PyYAML`，改用 Ruby 标准库解析 `team_cloud_go/deploy/kubernetes/team-cloud-go.yaml`，确认包含 `Secret`、`Deployment`、`Service` 三个文档。

## 文档更新计划

- `teamDoc/GAStep/06-team-cloud-go-service-steps.md`：记录 Go 重写追加工作包。
- `teamDoc/GAStep/progress-tracker.md`：追加 GTC-01 到 GTC-10 的实时状态。
- `teamDoc/README.md`、技术选型、目标架构、backlog、测试发布清单：改为 Go Team Cloud 服务端。
- `teamDoc/releaseManual/team-cloud-ga-release-manual.md`：已补充 Go 版服务端安装、环境变量、API 和 Kubernetes 部署说明。
