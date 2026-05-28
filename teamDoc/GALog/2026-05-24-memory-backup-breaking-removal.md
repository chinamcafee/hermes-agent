# 2026-05-24 `/memory-backup` 破坏性删除规划日志

## 背景

用户确认项目允许破坏性更新，旧 `/memory-backup` 入口不需要历史兼容。此前三方规划中仍保留了“隐藏别名”“迁移提示”之类的兼容措辞，需要收敛。

## 工作内容

- 将 ThreePartyUnionDevDoc 中 `/memory-backup` 迁移兼容口径改为破坏性删除。
- 在 Hermes Agent 运行时和 CLI 计划中补充后续编码删除清单。
- 更新 GTC-69、GTC-77、GTC-78 文档，明确 `/memory-backup` 不作为兼容入口保留。
- 更新 GAStep progress tracker，新增 GTC-79。
- 更新 Desktop Cloud Backup UI 方案，要求不再调用 `hermes memory-backup ...`。

## 当前状态

本轮只做文档规划，没有修改 CLI 或 Dashboard 代码。后续编码阶段应直接实现 `/cloud-backup` 并删除旧入口。
