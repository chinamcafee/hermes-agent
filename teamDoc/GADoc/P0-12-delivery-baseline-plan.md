# P0-12 交付基线计划

日期：2026-05-22
状态：Accepted for P1 execution
前置：`P0-11 风险登记册`

## 目标

冻结 P1-P5 work package 的 owner、依赖和目标周次，作为后续 GA 交付追踪基线。P0 视为 `W01-W03` 已完成；P1 从 `W04` 启动，GA sign-off 目标窗口为 `W42`，Post-GA backlog 整理为 `W43`。

## 工件

| 工件 | 用途 |
| --- | --- |
| [delivery-baseline-plan-v0.csv](artifacts/delivery-baseline-plan-v0.csv) | P1-P5 每个 work package 的 owner、依赖、目标周次。 |

## 阶段窗口

| Phase | 目标周次 | 目标 |
| --- | --- | --- |
| P1 平台基础 | `W04-W11` | Team Cloud 骨架、Casdoor、SpiceDB、PostgreSQL、MinIO、基础 Web/API。 |
| P2 记忆与 Hermes 集成 | `W12-W21` | 双层记忆、TeamMemoryProvider、runtime/gateway/web chat 接入。 |
| P3 数据治理与权限硬化 | `W22-W29` | 工具权限、个人备份、恢复、导出删除、审计、权限解释。 |
| P4 Beta 验证 | `W30-W37` | 部署硬化、观测、压测、安全测试、备份恢复演练、试点。 |
| P5 GA 发布 | `W38-W43` | 安全复测、SBOM/license、文档、Runbook、回归、sign-off。 |

## Owner 分组

| Owner group | 主要范围 |
| --- | --- |
| Platform Backend | Team API、AuthZ middleware、relationship outbox、组织/成员 API。 |
| Auth Backend | Casdoor OIDC、JWT、同步 worker、PAT/service account。 |
| Data Backend | PostgreSQL/pgvector、memory CRUD/query、workers。 |
| Runtime | Hermes core patch、TeamMemoryProvider、Gateway/API Server identity、tool hook。 |
| Frontend | Team Web Console、chat、permission explorer、admin UX。 |
| Security | 权限模型、负测、break-glass、工具权限、license/security review。 |
| SRE | compose/helm/offline、observability、backup restore、upgrade/rollback。 |
| QA | platform/security/isolation/load/final regression。 |
| Docs/Product/Release/Legal | 验收、文档、pilot、license、sign-off。 |

## 执行规则

1. CSV 中 `dependencies` 的前置项未完成时，不得将对应 work package 标为 `Done`。
2. `target_week` 是 baseline，不是承诺日期；任何变更必须在 progress tracker 的周报记录中说明。
3. Critical 风险触发时，对应 work package 状态改为 `Blocked` 或补充风险处置任务。
4. P4/P5 不允许新增未在 P0-10 验收矩阵覆盖的 GA blocker。
5. P1-P3 的核心 schema/权限/记忆变更必须同步更新 P0 工件或写 ADR amendment。

## 基线统计

- P1：22 个 work package，目标 `W04-W11`。
- P2：23 个 work package，目标 `W12-W21`。
- P3：22 个 work package，目标 `W22-W29`。
- P4：18 个 work package，目标 `W30-W37`。
- P5：15 个 work package，目标 `W38-W43`。
- 总计：100 个 work package。

## P1 启动入口

P1 的第一个执行项保持为 `P1-01 Team Cloud repo/package 骨架`。进入 P1 前必须确认：

- P0-01 到 P0-12 全部 `Done`。
- `teamDoc/GADoc/artifacts/` 下 schema、manifest、matrix、risk、baseline 工件均可读取。
- `progress-tracker.md` 已将 M0 标为完成或明确列出剩余 sign-off。

## 后续执行约束

- `progress-tracker.md` 是状态真相；本文件是 baseline。
- progress-tracker.md 是状态真相。
- 如果实际执行顺序偏离 CSV，必须先更新 `GALog` 说明原因，再更新 tracker。
- 每周周报必须至少引用当前 target week 的偏差和风险变化。
