# 16. GA 测试、发布和运维检查清单

## 1. 安全检查

- Casdoor JWT 校验测试通过。
- SpiceDB 权限矩阵正反测试通过。
- personal memory 跨成员访问 0 成功。
- team_shared memory 跨 org 访问 0 成功。
- MinIO backup 跨成员下载 0 成功。
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
- MinIO bucket restore 通过。
- Casdoor 配置恢复通过。
- 单成员 personal backup restore 通过。
- 组织导出回灌通过。

## 4. 发布包检查

- Docker Compose。
- Helm chart。
- Offline image bundle。
- `team_cloud_go/Dockerfile`。
- `team_cloud_go/deploy/kubernetes/team-cloud-go.yaml`。
- `team_cloud_go/dashboard/package-lock.json`。
- `team_cloud_go/dashboard/out/` 由 Docker build 生成，不手工发布。
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
- MinIO upload failure。
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

- `cd team_cloud_go && go test ./...` 通过。
- `cd team_cloud_go && go vet ./...` 通过。
- `cd team_cloud_go/dashboard && npm test -- --run` 通过。
- `cd team_cloud_go/dashboard && npm run type-check` 通过。
- `cd team_cloud_go/dashboard && npm run build` 通过并生成静态 export。
- PostgreSQL schema 测试覆盖 `tcg_organizations`、`tcg_members`、`tcg_memory_items`、`tcg_memory_review_items` 和 `tcg_backup_policies`。
- Kubernetes manifest 包含 `TEAM_CLOUD_DATABASE_URL`、`TEAM_CLOUD_DASHBOARD_DIR`、`/readyz` 和 `readOnlyRootFilesystem: true`。
- `/dashboard/`、`/dashboard/_next/*` 和 Dashboard SPA fallback 由 Go 服务托管。
