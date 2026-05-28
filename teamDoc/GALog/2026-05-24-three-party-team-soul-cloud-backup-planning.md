# 2026-05-24 三方团队父人格和 Cloud Backup 方案规划日志

## 背景

用户发现 Hermes Agent、Hermes Desktop 和 Team Cloud Go 之间缺少团队父人格、effective soul 展示和本地人格备份方案，同时要求将 `/memory-backup` 主入口迁移为 `/cloud-backup`，并按 memory/soul 分资源管理备份。

## 本轮动作

- 建立 Agent 侧 `teamDoc/ThreePartyUnionDevDoc/`。
- 建立 Desktop 侧 `teamDoc/ThreePartyUnionDevDoc/`。
- 将 Desktop 原 `05-agent-cloud-collaboration-topics.md` 和 `06-cli-bridge-team-cloud-boundary.md` 迁移到 Agent 侧 ThreePartyUnionDevDoc。
- 更新 Agent 侧 README、目标架构、CLI 边界和 Team Cloud Go 服务设计。
- 更新 Desktop 侧 README、当前状态排查、冲突矩阵、目标架构和实施路线图。

## 固化原则

```text
Team Cloud Go team parent soul
  -> Hermes Agent effective soul resolver
  -> Hermes Desktop read-only display through Bridge
```

本地 `SOUL.md` 和本地个人记忆均属于成员 profile 数据，由 `/cloud-backup soul ...` 和 `/cloud-backup memory ...` 备份到用户配置的 MinIO/S3-compatible 对象存储。
