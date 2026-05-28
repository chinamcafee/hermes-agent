# GTC-11 到 GTC-17 Go 服务端 GA 补强

日期：2026-05-23
状态：Implemented

> 2026-05-24 更新：本文“Service token”相关段落已被 GTC-60~64 取代。当前 Team Cloud Go 管理面使用无 token 首次初始化、Redis Dashboard session token 和 Casdoor/JWKS JWT，不再保留部署级 service token 作为 Dashboard 或业务 API 通道。

## 目标

补齐 `team_cloud/` 从最小 Team API 到 GA 服务端所需的关键能力面，使 Go 版不只提供成员和记忆 CRUD，还能覆盖认证、授权、审计、备份恢复、导出删除、工具策略和 runtime event bridge。

## 已实现范围

| ID | 能力 | Go 工件 | 验证 |
| --- | --- | --- | --- |
| GTC-11 | Casdoor 风格 JWT 鉴权 | `internal/authn/authn.go` | `TestCasdoorStyleJWTCanCallProtectedAPI` |
| GTC-12 | 授权关系和权限检查 API | `internal/store/store.go`、`internal/httpapi/server.go` | `TestGovernanceBackupExportDeletionToolPolicyAndAuthzAPIs` |
| GTC-13 | Audit 事件 API | `AppendAuditEvent`、`/v1/audit/events` | 同上 |
| GTC-14 | 个人备份恢复 API | `/v1/backups/personal/run`、restore preview/execute | 同上 |
| GTC-15 | 组织导出和删除请求 API | `/v1/exports/org`、`/v1/deletion-requests` | 同上 |
| GTC-16 | 工具策略和 runtime 事件 API | `/v1/tool-policy/evaluate`、`/v1/sessions`、`/v1/runtime/events` | 同上 |
| GTC-17 | PostgreSQL schema 扩展 | `tcg_audit_events`、`tcg_relationships`、`tcg_backup_jobs`、`tcg_org_exports`、`tcg_deletion_requests`、`tcg_tool_policy_rules`、`tcg_cloud_sessions`、`tcg_runtime_events` | `TestSchemaContainsCloudCollaborationTables` |

## 认证设计

Go 服务端当前支持两类入口：

- Dashboard session token：管理页帐号密码登录后签发 `hcs_...` opaque token，服务端在 Redis 中保存 token 摘要和 principal。
- Casdoor 风格 RS256 JWT：按 JWKS 校验 `kid`、签名、`iss`、`aud` 和 `exp`。

配置项：

- `TEAM_CLOUD_CASDOOR_ISSUER`
- `TEAM_CLOUD_CASDOOR_AUDIENCE`
- `TEAM_CLOUD_CASDOOR_JWKS_URL`

## 权限设计

当前实现提供 relationship write 和 permission check API，使用与 SpiceDB 一致的 resource/relation/subject 语义，并持久化到 PostgreSQL。它满足 Go 服务内部权限矩阵测试和解释路径输出，但远程 SpiceDB gRPC 适配仍应作为后续专门任务实现，避免为了 SDK 引入 Go 1.25 依赖破坏当前 Go 1.24 部署基线。

## 数据治理设计

- 个人备份只包含 `scope=personal` 且属于 `member_id` 的 active memory。
- 组织导出只统计 active `team_shared`，显式返回 `personal_count=0`。
- 删除请求当前支持 `personal_memory` scope，执行后将成员个人记忆标记为 `deleted`。
- 所有关键操作写入 audit event。

## 验证命令

```bash
cd team_cloud
go test ./...
go vet ./...
go build ./cmd/team-cloud-server
```
