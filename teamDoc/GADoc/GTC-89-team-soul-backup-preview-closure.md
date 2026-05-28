# GTC-89 团队父人格备份和恢复闭环

日期：2026-05-24
状态：Done

## 范围

本步骤修复 GA 复核发现的 Team Cloud Go 缺口：

- Dashboard 恢复团队记忆备份时必须先调用 `restore-preview`，再调用 `restore-execute`。
- Team Cloud Go 服务端补齐团队父人格备份策略、历史、手动备份、preview 和恢复执行 API。
- Team Cloud Go 删除请求 scope 改为 allowlist，只接受 `team_memory` 和 `team_soul`；`personal_memory`、大小写变体、前后空格变体和未知 scope 均返回 `unsupported_deletion_scope`。个人记忆继续只由本地 Hermes profile 和 `/cloud-backup memory` 管理。
- Dashboard “备份管理”同时展示团队记忆备份和团队父人格备份，不再是单一团队记忆视图。
- Go 备份 exporter 从 `.gitignore` 的 `export*` 规则中显式放行，避免 `team_cloud/internal/backup/exporter.go` 和测试被误忽略。
- 团队记忆加密备份文件头统一为 `HERMES-TEAM-MEMORY-BACKUP-V1`，不再沿用个人记忆备份头。

## API

新增团队父人格备份 API：

```text
GET  /v1/team-soul-backup-policy
PUT  /v1/team-soul-backup-policy
GET  /v1/backups/team-soul
POST /v1/backups/team-soul/run
POST /v1/backups/team-soul/{id}/restore-preview
POST /v1/backups/team-soul/{id}/restore-execute
```

团队父人格备份使用 `member_id=__team_soul__` 作为当前 schema 的资源哨兵，snapshot 保存在 `backup_jobs.manifest.team_soul`；启用 S3/MinIO 时对象 key 使用 `org/<org_id>/team-soul/...`。

## 验证

```bash
cd team_cloud && go test ./internal/backup ./internal/store ./internal/httpapi
cd team_cloud && go test ./...
cd team_cloud/dashboard && npm test -- --run
cd team_cloud/dashboard && npm run type-check
```

以上命令已在本步骤开发期间通过。
