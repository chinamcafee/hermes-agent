# P0-10 GA 验收矩阵

日期：2026-05-22
状态：Accepted for P0 execution
前置：`P0-09 MinIO 备份模型 v0`

## 目标

冻结企业版团队功能 GA 的验收矩阵，覆盖安全、性能、备份恢复、发布、文档、Beta/Pilot 和最终 sign-off。该矩阵是 P4 Beta Exit 和 P5 GA Sign-off 的硬门槛。

## 工件

| 工件 | 用途 |
| --- | --- |
| [ga-acceptance-matrix-v0.csv](artifacts/ga-acceptance-matrix-v0.csv) | 可追踪验收矩阵，后续填测试报告/owner/sign-off。 |

## 验收域

| 域 | GA 门槛 |
| --- | --- |
| Security | AuthN/AuthZ、个人记忆隔离、团队记忆跨租户隔离、备份访问、工具权限、break-glass 全部正反测试通过。 |
| Performance | Team API、memory prefetch、SpiceDB check、pgvector、backup worker、outbox lag 均有基线和告警。 |
| BackupRestore | PostgreSQL、SpiceDB、MinIO、Casdoor、个人恢复、组织导出均完成演练。 |
| Release | compose、Helm、offline bundle、SBOM、license、upgrade/rollback 均可交付。 |
| Documentation | 安装、管理员/用户、API、Runbook 覆盖 GA 功能面。 |
| Pilot | 至少 3 个试点团队运行 2 周，无数据泄漏，无未解决 P0/P1。 |
| Signoff | 产品、AuthN/AuthZ、Memory、Backup、Docs、Security、Pilot owner 明确签字。 |

## Blocker 规则

1. `ga_blocking=true` 的验收项必须全部通过，否则不得进入 GA。
2. `ga_blocking=false` 的验收项可以进入 Post-GA backlog，但必须有 owner、风险说明和目标版本。
3. 任一跨租户、跨成员 personal memory、个人备份越权读取问题直接阻断 GA。
4. 任一没有审计的高危工具 allow、break-glass、数据删除或导出操作直接阻断 GA。
5. SBOM、许可证报告、安装指南、备份恢复 Runbook 缺失直接阻断 GA。

## 证据要求

| 证据类型 | 要求 |
| --- | --- |
| Automated tests | 命令、提交、报告路径、通过率。 |
| Load tests | 数据规模、并发、P95/P99、错误率、环境。 |
| Restore drills | RPO/RTO、步骤、失败注入、校验结果。 |
| Security review | findings、severity、修复链接、残留风险。 |
| Docs review | reviewer、覆盖章节、缺口。 |
| Pilot report | 试点范围、运行周期、事故、P0/P1 bug 状态。 |
| Sign-off | owner、日期、条件。 |

## 最小统计

当前 v0 矩阵包含：

- 32 个验收项。
- 7 个验收域。
- 30 个 GA blocking 项。
- 2 个可带风险进入 Post-GA backlog 的非 blocking 项。

## 后续执行约束

- `P4-18 Beta exit report` 必须逐项引用本矩阵。
- `P5-08 GA sign-off` 必须只在 blocking 项全部通过后完成。
- `P5-14 Legal/compliance package` 必须覆盖 `GA-REL-004`。
- 新增 GA 功能必须新增或更新矩阵项，不能只在实现 PR 中隐式验收。
