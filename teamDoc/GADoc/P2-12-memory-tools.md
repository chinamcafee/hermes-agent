# P2-12 Memory tools

日期：2026-05-22
状态：Implemented
前置：`P2-11 TeamMemoryProvider 插件`

## 目标

本步骤在 `TeamMemoryProvider` core 上补齐 Hermes memory tools 暴露能力，覆盖 search、remember、propose、promote、forget、backup_now 的 schema 和 JSON string handler routing。该实现保持在 `team_cloud/memory/provider.py` 中，供后续 standalone Team Cloud memory plugin 或 core 集成点复用。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/memory/provider.py` | 工具 schema、tool call routing、写操作权限检查和 Team Cloud HTTP 转发。 |
| `tests/team_cloud/test_team_memory_provider_tools.py` | 覆盖 schema 暴露、search 转发、personal remember 权限检查、team propose deny。 |
| `teamDoc/GALog/2026-05-22-p2-12-memory-tools.md` | TDD 红绿记录和回归证据。 |
| `teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json` | 将 memory tools 纳入 smoke matrix。 |
| `scripts/team-cloud-foundation-smoke.sh` | 将 P2-12 测试纳入本地 smoke 回归。 |

## 行为

- `get_tool_schemas()`：
  - 暴露 `team_memory_search`、`team_memory_remember`、`team_memory_propose`、`team_memory_promote`、`team_memory_forget`、`team_memory_backup_now`。
  - 每个 schema 使用 OpenAI function style 的 object parameters。
- `handle_tool_call()`：
  - inactive 时 fail closed，返回 `{"success": false, "error": "inactive"}`。
  - unknown tool 返回 `{"success": false, "error": "unknown_tool"}`。
  - 所有返回值均为 JSON string。
- `team_memory_search`：
  - 调用 `/v1/memory/prefetch`。
  - payload 继承 `TeamContext` 并允许 tool args 覆盖 limit。
- `team_memory_remember`：
  - 写入 personal memory 前检查 `memory.personal.write`。
  - 调用 `/v1/memory`，scope 固定为 `personal`，subject 固定为当前 member。
- `team_memory_propose` 和 `team_memory_promote`：
  - 写入或提升 team_shared candidate 前检查 `memory.team.propose`。
  - team_shared 默认仍进入后端 review 流程，审核 API 已由 P2-08 承接。
- `team_memory_forget`：
  - 走 archive endpoint，保留 hard delete 给 P3 数据治理 worker。
- `team_memory_backup_now`：
  - 调用 personal backup trigger endpoint。
  - 备份策略、加密 exporter、MinIO 生命周期由 P3-05 到 P3-09 承接。

## 权限边界

本步骤只提供 provider-side 的 permission checker hook，并在写操作前调用；真实 SpiceDB 策略、审批和工具审计属于 P3 权限硬化范围。未注入 checker 时默认允许，方便 standalone plugin 在不同部署模式中接入自己的授权实现。

## 非目标

- 不创建 in-tree `plugins/memory/team_cloud/` provider 目录。
- 不实现 SpiceDB 细粒度 policy；P3 承接。
- 不实现 backup exporter 或 restore；P3 承接。
- 不把工具注册到 AIAgent；后续 runtime 集成步骤承接。

## 验证

- 红灯：新增 `tests/team_cloud/test_team_memory_provider_tools.py` 后，焦点测试因 `permission_checker` 参数缺失失败。
- 绿灯：补齐 provider tool schemas、routing 和 permission checker 后，焦点测试通过。
- 回归：P2-12 测试加入 smoke matrix 和 `scripts/team-cloud-foundation-smoke.sh`。
