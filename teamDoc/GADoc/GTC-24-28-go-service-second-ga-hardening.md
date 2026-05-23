# GTC-24 到 GTC-28 Go 服务二次 GA 硬化

## 范围

本轮补齐二次 GA 复核发现的阻塞项，继续保持 Python `team_cloud/` 不修改。

## 已完成项

- GTC-24：高风险治理 API 授权硬化。
  - authz relationship 写入要求 service token 或 org admin。
  - audit 读取、review queue、backup detail、deletion execute、runtime event 和组织列表按 JWT principal 做租户和资源归属授权。
  - JWT 请求不再信任请求体中的 `actor_member_id` 作为授权依据。
- GTC-25：对象存储恢复闭环。
  - S3/MinIO object store 增加 `GET`。
  - restore preview/execute 在对象模式下读取对象、校验 checksum、解密 AES-GCM JSONL，并刷新 backup snapshot。
- GTC-26：PostgreSQL pgvector SQL 检索。
  - Postgres backend 在 `query_embedding` 存在时使用 `embedding <=> $vector` SQL 排序。
  - 生产向量维度约束为 1536。
- GTC-27：Restore mode 执行语义。
  - `merge`：跳过已存在同内容 personal memory。
  - `overwrite`：先删除当前 active personal memory，再恢复备份。
  - `archive_current_then_restore`：先归档当前 active personal memory，再恢复备份。
- GTC-28：Backup cadence 和 retention 闭环。
  - enabled policy 按 `next_run_at` 到期执行。
  - 成功后写入 `last_run_at`/`next_run_at`。
  - 每次生成 backup job 后按 `retention_count` 将旧 job 标记为 `pruned`。

## 验证

已运行并通过：

```bash
cd team_cloud_go
go test ./internal/httpapi ./internal/backup ./internal/objectstore ./internal/store/postgres -count=1
```

关键新增测试：

- `TestJWTGovernanceAPIsRequireAdminRelationship`
- `TestJWTTenantBackupDeletionAndRuntimeGuards`
- `TestRestorePreviewValidatesEncryptedObjectStorePayload`
- `TestRestoreModesOverwriteAndArchiveCurrentThenRestore`
- `TestScheduledBackupRunnerRunsEnabledPolicies`
- `TestBackupRetentionPrunesOlderJobs`
- `TestPrefetchUsesPgvectorSQLWhenQueryEmbeddingIsProvided`
