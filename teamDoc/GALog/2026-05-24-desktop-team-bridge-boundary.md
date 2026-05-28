# 2026-05-24 Desktop Team Bridge 边界文档日志

## 背景

用户提出 Hermes Desktop 原则上不直连 Team Cloud Go，而是由 Hermes CLI/API Server 连接 Team Cloud 并向 Desktop 暴露服务。需要判断该方案是否符合 Desktop 当前设计，并在符合时同步完善 `hermes-agent` 与 `hermes-desktop` 文档。

## 判断

该方案符合 Desktop 当前职责：Desktop 是 Hermes Agent runtime 的桌面控制面，不应成为 Team Cloud Go 的第二套业务客户端。

## 本轮文档变更

- Agent 侧新增 `teamDoc/20-desktop-team-bridge-boundary.md`。
- Agent 侧新增 `teamDoc/GADoc/GTC-76-desktop-team-bridge-boundary.md`。
- Agent 侧更新 CLI 边界、Team Cloud Go 设计、目标架构和 release manual。
- Desktop 侧原 `teamDoc/06-cli-bridge-team-cloud-boundary.md` 后续已迁移：Desktop 保留消费契约到 `teamDoc/ThreePartyUnionDevDoc/03-desktop-bridge-consumption-contract.md`，Agent/Team Cloud Go 边界迁入 `hermes-agent/teamDoc/ThreePartyUnionDevDoc/91-migrated-cli-bridge-team-cloud-boundary.md`。
- Desktop 侧更新 README、当前状态排查、冲突矩阵、目标架构、路线图和联动专题。

## 固化原则

```text
Hermes Desktop -> Hermes Agent Runtime Bridge -> Team Cloud Go
```

Desktop 可打开 Team Cloud Dashboard，但不直接调用 Team Cloud Go 业务 API；成员登录、session token、team context、熔断、团队记忆 runtime 和个人记忆备份均归 Hermes Agent Bridge。
