# GTC-18 到 GTC-20 Go 服务 GA 收口记录

日期：2026-05-23

## 范围

本记录覆盖 Go Team Cloud 服务端 GA 复核中发现的三个阻塞面：

- 远程 SpiceDB/Authzed compatible 授权适配。
- JWT 业务 API 授权闭环和团队记忆读取过滤。
- 个人记忆加密 JSONL 备份对象、S3/MinIO 上传和恢复执行守卫。

## 实现结果

### GTC-18 远程授权适配

- 新增 `internal/authz`，支持 `TEAM_CLOUD_AUTHZ_MODE=local` 和 `TEAM_CLOUD_AUTHZ_MODE=spicedb_http`。
- `spicedb_http` 使用标准库 HTTP 调用 `/v1/relationships/write`、`/v1/permissions/check` 和 `/healthz`，避免引入会提升 Go toolchain 的 SDK 依赖。
- `/readyz` 同时检查 backend、authz 和 backup object store；远程授权不可用时 fail closed。

### GTC-19 业务授权闭环

- JWT principal 必须携带 `hermes_org_id` 和 `hermes_member_id`。
- 请求 payload/query 中的 `org_id`、`member_id` 不能越过 JWT scope。
- 组织、成员、团队、记忆、备份、导出、删除、工具策略、session 和 runtime 入口增加授权守卫。
- `team_shared` prefetch 对每条团队记忆执行 `read_team` 检查，无授权时过滤团队分区。
- service token 保留为内部 automation 通道。

### GTC-20 加密备份对象

- 新增 `internal/backup`，将 personal memory snapshot 编码为 JSONL 后使用 AES-256-GCM 加密。
- 新增 `internal/objectstore`，使用 Go 标准库实现 S3 Signature V4 path-style PUT/HEAD，可对接 MinIO。
- `TEAM_CLOUD_BACKUP_OBJECT_MODE=s3` 时，personal backup run 会上传 `.jsonl.enc` 对象并写回 manifest。
- 服务端启动后会按 `TEAM_CLOUD_BACKUP_SCHEDULER_INTERVAL_SECONDS` 扫描 enabled backup policy，并执行 scheduled personal backup。
- `tcg_backup_jobs` 增加 `object_uploaded` 和 `manifest`，`tcg_restore_previews` 持久记录 restore preview。
- `restore-execute` 未先执行 `restore-preview` 时返回 `restore_preview_required`。

## 验证证据

- `go test ./internal/authz ./internal/httpapi`
- `go test ./internal/backup ./internal/objectstore ./internal/config ./internal/deploy ./internal/store/postgres`

GTC-21 最终全量验证：

- `cd team_cloud_go && go test ./...`
- `cd team_cloud_go && go vet ./...`
- `cd team_cloud_go && go build ./cmd/team-cloud-server`
- Ruby YAML parse：`kubernetes yaml ok: Secret,Deployment,Service`
- `git diff --check -- team_cloud_go teamDoc`

以上命令已在 scheduled backup runner 补齐后重新执行并通过。
