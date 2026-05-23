# P2-11 TeamMemoryProvider 插件

日期：2026-05-22
状态：Implemented
前置：`P2-04 Prefetch pipeline`

## 目标

本步骤实现 TeamMemoryProvider 的核心适配器，覆盖 initialize、prefetch、sync_turn 和 inactive fail-closed。由于仓库 AGENTS 明确禁止新增 in-tree `plugins/memory/*` provider 目录，本步骤不创建 `plugins/memory/team_cloud/`，而是在 `team_cloud/memory/provider.py` 提供 standalone plugin 可复用的 provider core。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/memory/provider.py` | Team Cloud memory provider core、TeamContext、HTTP client protocol。 |
| `team_cloud/memory/__init__.py` | 导出 provider primitives。 |
| `tests/team_cloud/test_team_memory_provider.py` | inactive、prefetch、sync_turn 测试。 |
| `teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json` | 将 provider core 检查纳入 smoke matrix。 |
| `scripts/team-cloud-foundation-smoke.sh` | 将 P2-11 测试纳入本地 smoke 回归。 |

## 行为

- `is_available()`：
  - 要求 Team Cloud URL、service token 和完整 `TeamContext`。
  - 不发网络请求。
- `initialize()`：
  - 记录 session id。
  - 不污染未配置本地模式。
- `prefetch()`：
  - inactive 时返回空字符串。
  - active 时调用 `/v1/memory/prefetch`。
  - payload 包含 `query/org_id/member_id/team_id/project_id/limit`。
  - 返回格式化的 `Team Cloud memory` context block。
- `sync_turn()`：
  - inactive 时 no-op。
  - active 时调用 `/v1/memory/observations`。
  - observation 使用 `source=hermes_turn` 并保留 user/assistant messages。
- `get_tool_schemas()`：
  - 当前返回空列表；P2-12 承接 memory tools。

## 政策处理

原 P2 runtime plan 写有“新增 `plugins/memory/team_cloud/`”。该条与当前 AGENTS 政策冲突：新 memory backend 不能新增 in-tree provider 目录，应作为 standalone plugin 发布。本步骤保留 provider 核心实现并避免新增 in-tree plugin 目录；后续 standalone plugin 可 import 该核心实现或复制该契约。

## 非目标

- 不注册 memory plugin。
- 不实现 search/remember/propose/promote/forget/backup_now 工具；P2-12 承接。
- 不把 `team_context` 接入 AIAgent 初始化链；P2-14 承接。

## 后续衔接

- P2-12：在 provider core 上补齐 memory tool schemas 和 handler routing。
- P2-13：补齐 `/v1/memory/observations` API 与 turn metadata/context fencing。
- P2-14：将 `team_context` 从 AIAgent 初始化透传给 memory provider。
