# 2026-05-24 Team Soul Backup Preview Closure

## 背景

GA 复核指出两个阻断项：

- Dashboard “恢复所选备份”直接调用 `restore-execute`，而后端要求先执行 `restore-preview`。
- 团队父人格已经有治理页，但服务端和 Dashboard 尚未提供团队父人格备份、历史和恢复闭环。

## 本次工作

- 为 Go HTTP API 增加团队父人格备份策略、手动备份、历史、preview 和 restore execute。
- 为 memory store 和 PostgreSQL store 增加 `__team_soul__` 资源哨兵、team soul snapshot manifest、恢复 preview gate 和 upsert 恢复逻辑。
- Dashboard client 的团队记忆恢复改为 preview + execute；新增团队父人格备份 client 方法。
- Dashboard “备份管理”改为团队记忆和团队父人格双栏视图，各自拥有策略摘要、历史、立即备份、恢复和设置入口。
- `deletion_scope` 改为规范化 allowlist，只允许 `team_memory` 和 `team_soul`；`personal_memory`、大小写/空格变体和未知 scope 均返回 `unsupported_deletion_scope`，确保 Team Cloud Go 不再管理个人记忆删除。
- `.gitignore` 对 `team_cloud/internal/backup/exporter.go` 和 `exporter_test.go` 显式放行，避免根目录 `export*` 规则误忽略 Go 备份实现。
- 团队记忆加密备份文件头改为 `HERMES-TEAM-MEMORY-BACKUP-V1`，并用测试固定，不再复用个人记忆备份头。
- 更新 `teamDoc` 权威设计、Dashboard V2 设计、release manual、minikube manual 和进度追踪。

## 验证

```bash
cd team_cloud && go test ./internal/backup ./internal/store ./internal/httpapi
cd team_cloud && go test ./...
cd team_cloud/dashboard && npm test -- --run
cd team_cloud/dashboard && npm run type-check
```

当前阶段均通过。
