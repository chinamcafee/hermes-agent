# GTC-77 三方团队父人格和 Cloud Backup 方案规划

日期：2026-05-24

## 需求

用户要求重新核对 Hermes Agent、Hermes Desktop 和 Team Cloud Go 三方职责，补齐：

- 团队父人格作为本地人格的父人格。
- team mode 下展示团队父人格、本地人格、合并后人格结果。
- 团队父人格在 Team Cloud Go Dashboard 中管理和备份。
- 本地人格与本地记忆一样支持 MinIO/S3-compatible 定时和手动备份。
- CLI 备份一级入口从 `/memory-backup` 破坏性替换为 `/cloud-backup`，并按 `memory`、`soul` 分资源执行。
- Desktop 相关方案写入 Desktop ThreePartyUnionDevDoc；Agent/Team Cloud Go 方案写入 Agent ThreePartyUnionDevDoc。
- Desktop 中涉及 CLI 和 Team Cloud Go 的旧联动文档迁移到 Agent ThreePartyUnionDevDoc。

## 文档产物

Agent 侧：

- `teamDoc/ThreePartyUnionDevDoc/README.md`
- `teamDoc/ThreePartyUnionDevDoc/01-three-party-scope-and-decisions.md`
- `teamDoc/ThreePartyUnionDevDoc/02-team-parent-soul-domain-design.md`
- `teamDoc/ThreePartyUnionDevDoc/03-hermes-agent-runtime-cli-cloud-backup-plan.md`
- `teamDoc/ThreePartyUnionDevDoc/04-team-cloud-go-soul-api-dashboard-backup-plan.md`
- `teamDoc/ThreePartyUnionDevDoc/05-three-party-contracts-roadmap-tests.md`
- `teamDoc/ThreePartyUnionDevDoc/90-migrated-desktop-agent-cloud-collaboration-topics.md`
- `teamDoc/ThreePartyUnionDevDoc/91-migrated-cli-bridge-team-cloud-boundary.md`

Desktop 侧：

- `teamDoc/ThreePartyUnionDevDoc/README.md`
- `teamDoc/ThreePartyUnionDevDoc/01-desktop-team-soul-ui-plan.md`
- `teamDoc/ThreePartyUnionDevDoc/02-desktop-cloud-backup-ui-plan.md`
- `teamDoc/ThreePartyUnionDevDoc/03-desktop-bridge-consumption-contract.md`

## 关键结论

- Team Cloud Go 是团队父人格权威源。
- Hermes Agent 是 effective soul 合成者和 `/cloud-backup` 执行者。
- Desktop 是 Hermes Agent Bridge 消费者，不直连 Team Cloud Go。
- `/memory-backup` 不进入迁移兼容期；后续编码直接删除该入口，新主入口是 `/cloud-backup memory ...` 和 `/cloud-backup soul ...`。
- 本地人格备份对象与本地记忆备份对象必须使用不同 prefix。
