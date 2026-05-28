# P2-12 Memory tools

日期：2026-05-22
状态：Implemented
前置：`P2-11 TeamMemoryProvider 插件`

## 目标

本步骤在 `TeamMemoryProvider` core 上补齐 Hermes memory tools 暴露能力。2026-05-24 后，GA 实现只保留 search、add、propose、promote、forget 的团队记忆 schema 和 JSON string handler routing；旧 personal remember / backup_now 能力已退役。当前实现位于 `agent/team_memory_provider.py`，由 `agent/agent_init.py` 在 team mode 下挂载。

> 2026-05-24 边界更新：GTC-69 后 GA 主路径已移除云端 `team_memory_remember` 和 `team_memory_backup_now`。GTC-77 后个人记忆由 `/cloud-backup memory` 写入用户自有 MinIO/S3-compatible 地址，本地人格由 `/cloud-backup soul` 管理；Team Cloud tools 只负责团队记忆。

## 工件

| 工件 | 用途 |
| --- | --- |
| `agent/team_memory_provider.py` | 工具 schema、tool call routing、团队记忆写入和 Team Cloud HTTP 转发。 |
| `tests/hermes_cli/test_team_memory_provider_tools.py` | 覆盖 schema 暴露、search 转发、team add/propose/forget 和 personal 工具退役。 |
| `teamDoc/GALog/2026-05-22-p2-12-memory-tools.md` | TDD 红绿记录和回归证据。 |
| `teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json` | 将 memory tools 纳入 smoke matrix。 |
| `scripts/team-cloud-foundation-smoke.sh` | 将 P2-12 测试纳入本地 smoke 回归。 |

## 行为

- `get_tool_schemas()`：
  - 当前 GA 主路径暴露 `team_memory_search`、`team_memory_add`、`team_memory_propose`、`team_memory_promote`、`team_memory_forget`。
  - 每个 schema 使用 OpenAI function style 的 object parameters。
- `handle_tool_call()`：
  - inactive 时 fail closed，返回 `{"success": false, "error": "inactive"}`。
  - unknown tool 返回 `{"success": false, "error": "unknown_tool"}`。
  - 所有返回值均为 JSON string。
- `team_memory_search`：
  - 调用 `/v1/memory/prefetch`。
  - payload 继承 `TeamContext` 并允许 tool args 覆盖 limit。
- `team_memory_add`：
  - 用户显式要求新增团队记忆时调用。
  - 调用 `/v1/memory`，scope 固定为 `team_shared`，status 固定为 `active`，source_type 固定为 `admin_created`。
- `team_memory_propose` 和 `team_memory_promote`：
  - 写入或提升 team_shared candidate 前检查 `memory.team.propose`。
  - team_shared 默认仍进入后端 review 流程，审核 API 已由 P2-08 承接。
- `team_memory_forget`：
  - 走 archive endpoint，保留 hard delete 给 P3 数据治理 worker。
- `team_memory_backup_now`：
  - 已退役；本地个人记忆备份由 `/cloud-backup memory` 负责，团队记忆备份由 Dashboard “备份管理”负责。

## 权限边界

本步骤只提供 provider-side 的 permission checker hook，并在写操作前调用；真实 SpiceDB 策略、审批和工具审计属于 P3 权限硬化范围。未注入 checker 时默认允许，方便 standalone plugin 在不同部署模式中接入自己的授权实现。

## 非目标

- 不创建 in-tree `plugins/memory/team_cloud/` provider 目录。
- 不实现 SpiceDB 细粒度 policy；P3 承接。
- 不实现 backup exporter 或 restore；P3 承接。
- 不把工具注册到 AIAgent；后续 runtime 集成步骤承接。

## 验证

- 回归：`venv/bin/python -m pytest tests/hermes_cli/test_team_memory_provider.py tests/hermes_cli/test_team_memory_provider_tools.py -q`
