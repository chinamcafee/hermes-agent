# GAStep：从 0 到 GA 的编码改造步骤

本目录把 `teamDoc` 中的 GA 方案转换成可执行的研发工作步骤。目标是从当前 `hermes-agent` 状态出发，逐步完成 `Casdoor + SpiceDB + PostgreSQL/pgvector + MinIO + Team Cloud + Hermes runtime` 的 GA 品质改造。

## 使用方式

1. 先读 [01-work-package-register.md](01-work-package-register.md)，确认全部工作包、依赖和人周估算。
2. 按阶段执行 [02-phase-0-1-foundation-steps.md](02-phase-0-1-foundation-steps.md)、[03-phase-2-memory-runtime-steps.md](03-phase-2-memory-runtime-steps.md)、[04-phase-3-governance-steps.md](04-phase-3-governance-steps.md)、[05-phase-4-5-beta-ga-steps.md](05-phase-4-5-beta-ga-steps.md)。
3. Go 服务端替代 Python `team_cloud/` 的追加工作按 [06-team-cloud-go-service-steps.md](06-team-cloud-go-service-steps.md) 执行；该追加项允许破坏性更新，因为 Python 版从未上线部署。
4. 每周更新 [progress-tracker.md](progress-tracker.md)，只更新状态、负责人、日期、阻塞项和证据链接。

## 估算口径

- 单位：人周，包含设计、编码、自测、代码评审、集成测试和文档更新。
- 总量：约 `205-230 人周`，按 6-8 人团队并行，日历周期约 `7-9 个月`。
- 粒度：每个工作包通常为 `0.5-4 人周`，可直接进入 issue tracker。
- 质量门槛：每个工作包必须满足 Definition of Done，不能只提交代码不提交测试、文档和验收证据。

## 阶段总览

| 阶段 | 目标 | 工作包数 | 估算 |
| --- | --- | ---: | ---: |
| P0 架构冻结 | 冻结 GA 边界、ADR、schema、验收矩阵 | 12 | 12 人周 |
| P1 平台基础 | Casdoor、SpiceDB、PostgreSQL、MinIO、Team API、基础管理台 | 22 | 47 人周 |
| P2 记忆与 Hermes 集成 | 双层记忆、pgvector、TeamMemoryProvider、Gateway/API/Web chat | 23 | 59 人周 |
| P3 数据治理与权限硬化 | 工具权限、个人备份、导出删除、break-glass、审计 | 22 | 49 人周 |
| P4 Beta 验证 | 部署包、压测、安全测试、观测、试点 | 18 | 28 人周 |
| P5 GA 发布 | 发布文档、Runbook、SBOM、最终回归和签字 | 15 | 18 人周 |
| GTC Go 服务端重写 | 用 Go 服务替代未上线的 Python Team Cloud，补齐 K8s 部署形态 | 10 | 追加需求 |

## Definition of Done

每个工作包默认完成标准：

- 代码合入目标分支。
- 单元测试和相关集成测试通过。
- 权限、安全、租户隔离相关逻辑有反向测试。
- 迁移、配置、环境变量和部署说明更新。
- 审计或观测事件按设计落地。
- 进度追踪文档更新状态和证据链接。
