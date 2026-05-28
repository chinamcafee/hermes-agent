# 16. GA 测试、发布和运维检查清单

## 1. 安全检查

- Casdoor JWT 校验测试通过。
- SpiceDB 权限矩阵正反测试通过。
- Team Cloud 不暴露云端 personal memory 读写入口；个人记忆只在本地 profile。
- team_shared memory 跨 org 访问 0 成功。
- CLI 个人记忆备份凭据不进入 Team Cloud Dashboard。
- 高危工具绕过测试 0 成功。
- break-glass 审批和通知测试通过。

## 2. 性能检查

- Team API P95 达标。
- memory prefetch P95 <= 500ms。
- SpiceDB check P95 <= 30ms。
- pgvector 查询 P95 有基线。
- backup worker 处理能力满足最大租户规模。
- outbox lag 有告警阈值。

## 3. 备份恢复检查

- PostgreSQL PITR 演练通过。
- SpiceDB relationship snapshot + outbox replay 通过。
- 可选团队记忆对象存储 restore 通过。
- Casdoor 配置恢复通过。
- CLI 单 profile personal backup restore 通过。
- 组织导出回灌通过。

## 4. 发布包检查

- Docker Compose。
- Kubernetes manifest。
- minikube runbook。
- offline bundle。
- Offline image bundle。
- `team_cloud/Dockerfile`。
- `team_cloud/deploy/kubernetes/team-cloud-go.yaml`。
- `team_cloud/dashboard/package-lock.json`。
- `team_cloud/dashboard/out/` 由 Docker build 生成，不手工发布。
- SBOM。
- License report。
- Migration guide。
- Upgrade guide。
- Rollback guide。
- Security hardening guide。

## 5. 运维 Runbook

- Casdoor JWKS rotation failure。
- SpiceDB unavailable。
- PostgreSQL slow pgvector query。
- Optional object-store upload failure。
- Outbox dead letter。
- Backup restore failure。
- Cross-tenant access alert。
- Destructive tool abuse alert。

## 6. GA Sign-off

| 领域 | Owner | 状态 |
| --- | --- | --- |
| Product requirements | Product | signed |
| AuthN/AuthZ | Backend + Security | signed |
| Memory isolation | Runtime + QA | signed |
| Backup/restore | SRE | signed |
| Web Console | Frontend | signed |
| Documentation | Product + Engineering | signed |
| Security review | Security | signed |
| Pilot acceptance | Customer/Internal | signed |
| Release operations | Release | signed |

M5 GA Sign-off 已关闭，最终证据见 `teamDoc/GADoc/artifacts/release/team-cloud-ga-sign-off-v0.json`。

## 7. Go Team Cloud 追加验证

- `cd team_cloud && go test ./...` 通过。
- `cd team_cloud && go vet ./...` 通过。
- `cd team_cloud/dashboard && npm test -- --run` 通过。
- `cd team_cloud/dashboard && npm run type-check` 通过。
- `cd team_cloud/dashboard && npm run build` 通过并生成静态 export。
- PostgreSQL schema 测试覆盖 `tcg_organizations`、`tcg_members`、`tcg_memory_items`、`tcg_memory_review_items` 和 `tcg_backup_policies`。
- Kubernetes manifest 包含 `TEAM_CLOUD_DATABASE_URL`、`TEAM_CLOUD_DASHBOARD_DIR`、`/readyz` 和 `readOnlyRootFilesystem: true`。
- `/dashboard/`、`/dashboard/_next/*` 和 Dashboard SPA fallback 由 Go 服务托管。
- Dashboard “备份管理”展示团队记忆和团队父人格备份历史、策略设置和恢复。
- Team Cloud 团队记忆恢复按 memory id upsert，重复恢复不产生重复记录。
- Hermes CLI `/cloud-backup memory|soul` 覆盖配置、周期、手动备份、历史和恢复。
