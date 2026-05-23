# Team Cloud Go 服务端 GA 补强日志

日期：2026-05-23

## 评估结论

上一轮 `team_cloud_go/` 已完成独立服务骨架、团队管理、双层记忆、review queue、个人备份策略、PostgreSQL 后端和 Kubernetes 部署资产，但按 `teamDoc` 的 GA 标准仍缺认证、授权、审计、备份恢复、导出删除、工具策略和 runtime 事件桥。因此继续推进补强。

## TDD 记录

红灯：

- 新增 `team_cloud_go/internal/httpapi/ga_capabilities_test.go`。
- 首次运行 `go test ./...` 失败于缺少 `CasdoorIssuer`、`CasdoorAudience`、`CasdoorJWKSURL` 配置字段和相关 API。

绿灯：

- 新增 `internal/authn`，支持 RS256/JWKS JWT 校验。
- 扩展 `store.Backend`，新增 audit、relationship/check、backup/restore、export/delete、tool policy、session/runtime event 方法。
- 扩展内存后端和 PostgreSQL 后端。
- 扩展 HTTP 路由：
  - `/v1/audit/events`
  - `/v1/authz/relationships`
  - `/v1/authz/check`
  - `/v1/backups/personal/run`
  - `/v1/backups/personal/{id}/restore-preview`
  - `/v1/backups/personal/{id}/restore-execute`
  - `/v1/exports/org`
  - `/v1/deletion-requests`
  - `/v1/deletion-requests/{id}/execute`
  - `/v1/tool-policy/evaluate`
  - `/v1/tool-policy/rules`
  - `/v1/sessions`
  - `/v1/runtime/events`
- 扩展 Kubernetes manifest，加入 Casdoor issuer、audience 和 JWKS URL 环境变量。

## 依赖决策

尝试评估 `github.com/authzed/authzed-go` 时发现当前可用版本链会将 Go module 提升到 Go 1.25 并拉入大量生成器和 lint 依赖。为保持 `team_cloud_go/Dockerfile` 的 Go 1.24 基线，本轮未引入该 SDK。远程 SpiceDB gRPC 适配应拆为后续任务，当前 Go 服务提供本地持久化 relationship/check 语义闭环。

## 新鲜验证

- `cd team_cloud_go && go test ./...` 已通过。

后续仍需在最终收尾前运行：

- `cd team_cloud_go && go vet ./...`
- `cd team_cloud_go && go build ./cmd/team-cloud-server`
- `git diff --check -- team_cloud_go teamDoc`
