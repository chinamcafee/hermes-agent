# GTC-69 Team Memory Backup Boundary

## 背景

本轮需求将 Team Cloud 和 Hermes CLI 的数据职责重新收敛。

> 2026-05-24 GTC-77/GTC-79 更新：本文件记录 GTC-69 当时的边界调整。后续三方联动方案把本地备份主入口从 `/memory-backup` 破坏性替换为 `/cloud-backup`，并新增 `soul` 资源类型。当前 GA 规划以 `teamDoc/ThreePartyUnionDevDoc/` 和 `/cloud-backup memory|soul` 为准，不保留 `/memory-backup` 兼容入口。

- Team Cloud 云端只管理团队记忆、成员、审计和团队级备份。
- 个人记忆仍由本地 Hermes CLI 管理，不进入 Team Cloud 云端管理面。
- 个人记忆和本地人格备份由 CLI `/cloud-backup memory|soul` 负责，写入用户配置的 MinIO/S3-compatible 地址。
- Team Cloud 的 MinIO/S3 仅作为团队记忆备份的可选托管对象存储，不再是服务端初始化和 Kubernetes 部署的必备组件。

## 产品边界

| 能力 | 归属 | 说明 |
| --- | --- | --- |
| 团队记忆 CRUD | Team Cloud Go + Dashboard | 管理员和超级管理员管理团队共享记忆。 |
| 团队记忆备份/恢复 | Team Cloud Go + Dashboard | 按团队记忆 ID 做 insert-or-update，重复恢复不产生重复记录。 |
| 个人记忆读写 | Hermes CLI 本地 | 使用 `tools/memory_tool.py` 的 profile-scoped `memories/MEMORY.md` 和 `memories/USER.md`。 |
| 个人记忆/本地人格备份恢复 | Hermes CLI `/cloud-backup memory|soul` | 备份到用户指定 MinIO；可手动、可由 Hermes cron 定时触发。 |
| MinIO/S3 | 可选依赖 | CLI 个人备份必须由用户配置；Team Cloud 只有启用团队备份对象存储时才需要。 |

## API 调整

Team Cloud 新增团队记忆备份 API：

- `GET /v1/team-memory-backup-policy?org_id=...`
- `PUT /v1/team-memory-backup-policy`
- `GET /v1/backups/team?org_id=...`
- `POST /v1/backups/team/run`
- `GET /v1/backups/team/{backup_id}`
- `POST /v1/backups/team/{backup_id}/restore-preview`
- `POST /v1/backups/team/{backup_id}/restore-execute`

旧的 `/v1/me/memory-backup-policy` 和 `/v1/backups/personal/*` 在 Go GA 主路径中删除，不作为 Dashboard、CLI 或 API 兼容入口保留。

## CLI 调整

`/cloud-backup` 是新的唯一一级备份 slash command，`/memory-backup` 直接删除：

- `status`：查看 MinIO 配置、最近备份和 cron job。
- `config`：设置 endpoint、bucket、region、prefix 和 access/secret env key。
- `memory schedule|backup|history|restore`：管理 `memories/MEMORY.md`、`memories/USER.md` 等本地个人记忆文件。
- `soul schedule|backup|history|restore`：管理当前 profile 的 `SOUL.md`。
- memory 和 soul 必须使用不同 object key prefix，恢复时校验 resource type。

Team Cloud 连接增加熔断：

- 默认 `auto`：连续失败达到阈值后自动打开熔断，冷却后自动半开重试。
- `manual_open`：用户手动暂停团队 API。
- `manual_closed`：用户手动恢复并强制允许请求。
- `/team breaker status|open|close|auto` 提供控制入口。

TeamMemoryProvider 运行时边界：

- 只向 Team Cloud 查询 `team_shared`；prefetch 请求固定 `include_personal=false`。
- 不再暴露 `team_memory_remember` 和 `team_memory_backup_now`。
- 显式“新增团队记忆”仍走 `team_memory_add` 并返回 `团队记忆已创建：<id> - <content>` notice。
- 自动抽取结果如果由服务端返回，会在 CLI 输出 `团队记忆已抽取：<id> - <content>`。

## Dashboard 调整

- “记忆治理”进入页面即自动刷新团队记忆和待审队列。
- “备份策略”更名为“备份管理”，只展示团队记忆备份策略、备份历史、立即备份和恢复入口。
- “权限中心”变成只读角色矩阵和服务端固定权限说明，不再提供关系写入或权限检查调试表单。
