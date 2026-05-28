# GTC-78 三方文档引用和备份入口一致性收敛

日期：2026-05-24

## 需求

在完成团队父人格、effective soul 和 `/cloud-backup` 三方规划后，需要复查旧文档中仍指向 Desktop 旧文件或仍把 `/memory-backup` 当作 GA 主入口的内容，避免后续实现阶段按历史文档执行。

> 2026-05-24 破坏性更新：用户明确允许删除 `/memory-backup`，因此不再规划兼容别名、隐藏命令或迁移提示。后续实现必须直接移除旧入口。

## 处理范围

- Agent 侧 `teamDoc/README.md`、目标架构、数据管理、Go 服务端设计、GA 产品需求、测试发布清单和 release manual。
- Agent 侧 `GAStep/progress-tracker.md`、Go 服务端步骤、Team Memory Backup 步骤。
- Desktop Bridge 相关旧文档路径引用。
- Desktop 侧 `teamDoc/ThreePartyUnionDevDoc/` 保留为桌面 UI 和 Bridge 消费方案；涉及 Agent/Team Cloud Go 的专题迁移到 Agent 侧。

## 收敛结论

- 新主入口是 `/cloud-backup`。
- `/cloud-backup memory ...` 管理当前 Hermes profile 的 `memories/`。
- `/cloud-backup soul ...` 管理当前 Hermes profile 的 `SOUL.md`。
- `/memory-backup` 必须被删除，不作为兼容别名、隐藏命令或迁移提示保留。
- Team Cloud Go 管理团队记忆和团队父人格；成员个人记忆和本地人格不进入 Team Cloud Dashboard。
- Team Cloud Go Dashboard 负责团队父人格编辑、版本、审计、备份和恢复；Desktop 只能通过 Hermes Agent Bridge 读取团队父人格和 effective soul。

## 文档迁移说明

原 `hermes-desktop/teamDoc/05-agent-cloud-collaboration-topics.md` 和 `hermes-desktop/teamDoc/06-cli-bridge-team-cloud-boundary.md` 已迁移：

- Agent/Team Cloud Go 权威边界：`teamDoc/ThreePartyUnionDevDoc/90-migrated-desktop-agent-cloud-collaboration-topics.md`
- CLI/API Bridge 权威边界：`teamDoc/ThreePartyUnionDevDoc/91-migrated-cli-bridge-team-cloud-boundary.md`
- Desktop 消费契约：`hermes-desktop/teamDoc/ThreePartyUnionDevDoc/03-desktop-bridge-consumption-contract.md`

## 验收

- Markdown link check 不应再指向已删除的 Desktop `05`、`06` 文档。
- 当前方案和 release manual 不应把 `/memory-backup` 描述为新增主入口或兼容入口。
- 历史 GADoc/GALog 中如保留 `/memory-backup`，必须标明这是历史事实；未来实现不保留该入口。
