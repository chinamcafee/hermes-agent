# ThreePartyUnionDevDoc 三方联动方案索引

日期：2026-05-24

本目录记录 `hermes-agent`、`team_cloud` 和 `hermes-desktop` 围绕团队父人格、本地人格、云端备份和 Desktop Bridge 的联动改造方案。本目录中的 Agent/Team Cloud Go 文档是服务端与 CLI 的权威规划；Desktop 侧只保留桌面 UI 和 Bridge 消费方案。

## 核心结论

- Team Cloud Go 新增“团队父人格”管理能力，父人格是团队模式下所有成员本地人格的上级约束。
- Hermes Agent 在 team mode 下自动同步团队父人格，并与本地 `SOUL.md` 合成有效人格；冲突时以团队父人格为准。
- team mode 下保存本地 `SOUL.md` 会触发 Hermes Agent 调用当前 profile 配置的大模型供应商生成合并后人格；模型不可用时返回优雅失败并使用安全降级组合。
- Hermes CLI 在 team mode 下提供一级人格入口，显示“团队父人格”“本地人格”“合并后人格结果”三个维度；非 team mode 只显示本地人格。
- 备份入口破坏性替换为 `/cloud-backup`。MinIO/S3-compatible 配置共用，备份资源分为 `memory` 和 `soul` 两类，路径分开。
- Team Cloud Go Dashboard 管理团队父人格和团队父人格备份；本地人格备份仍由 Hermes Agent CLI/Desktop 通过 `/cloud-backup soul ...` 管理。
- Hermes Desktop 不直连 Team Cloud Go；Desktop 只通过 Hermes Agent Runtime Bridge 展示团队父人格、本地人格、合并人格和云备份操作。

## 文档列表

| 文档 | 内容 |
| --- | --- |
| [01-three-party-scope-and-decisions.md](01-three-party-scope-and-decisions.md) | 三方职责边界、关键决策和非目标。 |
| [02-team-parent-soul-domain-design.md](02-team-parent-soul-domain-design.md) | 团队父人格的数据模型、合并规则、权限和同步语义。 |
| [03-hermes-agent-runtime-cli-cloud-backup-plan.md](03-hermes-agent-runtime-cli-cloud-backup-plan.md) | Hermes Agent CLI、运行时、`/cloud-backup` 和本地人格备份规划。 |
| [04-team-cloud-go-soul-api-dashboard-backup-plan.md](04-team-cloud-go-soul-api-dashboard-backup-plan.md) | Team Cloud Go API、Dashboard、数据库、备份和恢复规划。 |
| [05-three-party-contracts-roadmap-tests.md](05-three-party-contracts-roadmap-tests.md) | 三方 API/IPC/CLI 契约、阶段路线图和测试验收。 |
| [06-cli-desktop-model-provider-unification.md](06-cli-desktop-model-provider-unification.md) | CLI/TUI/Dashboard/Desktop 模型供应商清单统一和 Local Hermes Agent Runtime 方案。 |
| [90-migrated-desktop-agent-cloud-collaboration-topics.md](90-migrated-desktop-agent-cloud-collaboration-topics.md) | 从 Desktop teamDoc 迁移的 Agent/Team Cloud Go 联动专题。 |
| [91-migrated-cli-bridge-team-cloud-boundary.md](91-migrated-cli-bridge-team-cloud-boundary.md) | 从 Desktop teamDoc 迁移的 CLI/API Bridge 边界专题。 |

## 命名约定

- `team parent soul`：团队父人格，Team Cloud Go 侧的团队级人格基线。
- `local soul`：本地人格，当前 Hermes profile 的 `SOUL.md`。
- `effective soul`：合并后人格，Team 父人格 + 本地人格 + 明确优先级规则组成的最终系统人格段。
- `cloud backup`：本地个人资源备份入口，覆盖 `memory` 和 `soul` 两种 resource type。

## 破坏性替换原则

项目尚未上线部署，因此不保留 `/memory-backup` 兼容入口。后续编码时必须直接删除 slash command、顶层 CLI subcommand、旧配置键、旧模块入口和旧测试路径，并以 `/cloud-backup memory ...`、`/cloud-backup soul ...` 作为唯一备份入口。
