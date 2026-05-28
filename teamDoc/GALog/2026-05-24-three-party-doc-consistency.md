# 2026-05-24 三方文档一致性收敛日志

## 背景

三方联动方案新增团队父人格、本地人格备份和 `/cloud-backup` 后，旧文档中仍有部分内容指向 Desktop 已迁移文档，或仍把 `/memory-backup` 表述为 GA 主入口。

2026-05-24 补充：用户明确允许破坏性更新，因此 `/memory-backup` 不再保留兼容别名或迁移提示，后续实现直接删除。

## 工作内容

- 修复 `teamDoc/20-desktop-team-bridge-boundary.md`、GTC-76 GADoc、GTC-76 progress row 中的 Desktop 旧文档链接。
- 更新 GA 目标架构、云端数据管理、MinIO 本地备份、Go 服务端设计、产品需求和 release manual。
- 将本地备份职责统一表述为 `/cloud-backup memory|soul`。
- 在历史 GTC-69/GTC-70 文档中增加 GTC-77/GTC-79 后续更新说明，明确 `/memory-backup` 仅为历史实现事实，未来不作为兼容入口保留。
- 在 `progress-tracker.md` 增加 GTC-78，记录本轮仅文档规划和一致性收敛。

## 验收口径

- `teamDoc/ThreePartyUnionDevDoc/` 是 Agent/Team Cloud Go 权威方案。
- `hermes-desktop/teamDoc/ThreePartyUnionDevDoc/` 是 Desktop UI 与 Bridge 消费方案。
- 新文档、手册和后续实现计划使用 `/cloud-backup memory|soul`。
