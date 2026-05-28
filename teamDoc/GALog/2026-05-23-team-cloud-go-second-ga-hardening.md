# 2026-05-23 Team Cloud Go 二次 GA 硬化

## 背景

二次 GA 复核在 `team_cloud/` 当前实现中发现仍需补齐的阻塞项。Python `team_cloud/` 继续保持不修改，Go 服务端是首次上线部署目标。

## GTC-24 高风险治理 API 授权硬化

- 新增失败测试：
  - `TestJWTGovernanceAPIsRequireAdminRelationship`
  - `TestJWTTenantBackupDeletionAndRuntimeGuards`
- 红灯验证：
  - `go test ./internal/httpapi -run 'TestJWT(GovernanceAPIsRequireAdminRelationship|TenantBackupDeletionAndRuntimeGuards)' -count=1`
  - 失败原因：普通 JWT 成员可写 authz relationship；普通 JWT 组织列表返回跨租户组织。
- 实现方向：
  - authz relationship 写入、audit 读取、review queue、backup detail、deletion execute、runtime event 都改为先读取资源归属，再基于 JWT principal 和 relationship/check 授权。
  - `actor_member_id` 不再作为 JWT 授权依据，JWT 请求使用 token 中的 `hermes_member_id`。

绿灯验证：

- `go test ./internal/httpapi -run 'TestJWT(GovernanceAPIsRequireAdminRelationship|TenantBackupDeletionAndRuntimeGuards)' -count=1`

## GTC-25 对象存储恢复闭环

- 新增 `ObjectStore.Get` 和 S3/MinIO path-style GET。
- 新增 AES-GCM JSONL 解密入口。
- restore preview/execute 在对象模式下读取对象、校验 `checksum_sha256`、解密 JSONL 并刷新 backup snapshot。
- 红灯：篡改对象时 preview 仍成功。
- 绿灯：篡改对象返回 `backup_object_checksum_mismatch`。

## GTC-26 PostgreSQL pgvector SQL 检索

- Postgres backend 在 `query_embedding` 存在时使用 `embedding <=> $vector` SQL 排序。
- 新增静态测试约束 pgvector SQL 路径，避免回退到应用层全量排序。
- 生产 Postgres embedding/query_embedding 维度约束为 1536。

## GTC-27 Restore mode 执行语义

- `merge` 保持只创建缺失项。
- `overwrite` 先将当前 active personal memory 标记为 deleted，再恢复备份。
- `archive_current_then_restore` 先将当前 active personal memory 标记为 archived，再恢复备份。

## GTC-28 Backup cadence 和 retention 闭环

- Backup policy 增加 `last_run_at` 和 `next_run_at`。
- scheduler 只执行到期 policy。
- backup job 增加 `created_at`，每次生成后按 `retention_count` 标记旧 job 为 `pruned`。

## 验证证据

- `go test ./internal/httpapi ./internal/backup ./internal/objectstore ./internal/store/postgres -count=1` 通过。

## GTC-29 最终 GA 复核

已运行并通过：

- `cd team_cloud && go test ./...`
- `cd team_cloud && go vet ./...`
- `cd team_cloud && go build ./cmd/team-cloud-server`
- `cd team_cloud && ruby -e 'require "yaml"; docs = YAML.load_stream(File.read("deploy/kubernetes/team-cloud-go.yaml")); puts "kubernetes yaml ok: #{docs.map { |d| d["kind"] }.join(",")}"'`
- `git diff --check -- team_cloud teamDoc`
- `rg -n 'authzed|golangci|mage|go1\.25|v0\.45\.0|v0\.36\.0' team_cloud/go.mod team_cloud/go.sum` 无命中。

构建产物 `team_cloud/team-cloud-server` 已清理。

## 状态

GTC-24 到 GTC-29 已完成实现和最终验证，Go 服务端达到本轮 GA 状态。
