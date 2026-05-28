# P2-11 TeamMemoryProvider 插件

日期：2026-05-22
状态：Implemented
前置：`P2-04 Prefetch pipeline`

> 2026-05-24 更新：Team Cloud Go Dashboard 和 Go 服务端管理面已取消部署级 service token。本文早期 provider core 中的 service token 可用性描述仅代表 P2 阶段 Python 适配器历史口径；后续 CLI / provider 接入应改用成员级 token、OIDC/JWT 或 PAT。

> 2026-05-24 追加更新：CLI team mode 已把该 provider core 升级为 first-party 自动挂载运行时，不再要求额外安装 `plugins/memory/team_cloud`。实现记录见 `GTC-68-cli-team-memory-runtime.md`。

> 2026-05-24 边界更新：GTC-69 后 Team Cloud provider 只召回和写入 `team_shared`，prefetch 固定 `include_personal=false`。云端 personal remember 和 personal backup 工具已退役；GTC-77 后个人记忆和本地人格由本地 Hermes profile 和 `/cloud-backup memory|soul` 管理。

## 目标

本步骤实现 TeamMemoryProvider 的核心适配器，覆盖 initialize、prefetch、sync_turn 和 inactive fail-closed。当前 GA 实现已经迁入 `agent/team_memory_provider.py`，由 Hermes Agent team mode first-party 自动挂载；旧 `team_cloud/memory/provider.py` 已删除。

## 工件

| 工件 | 用途 |
| --- | --- |
| `agent/team_memory_provider.py` | Team Cloud memory provider core、TeamContext、HTTP client protocol。 |
| `agent/agent_init.py` | team mode 下自动初始化 TeamMemoryProvider。 |
| `tests/hermes_cli/test_team_memory_provider.py` | inactive、prefetch、sync_turn 测试。 |
| `teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json` | 将 provider core 检查纳入 smoke matrix。 |
| `scripts/team-cloud-foundation-smoke.sh` | 将 P2-11 测试纳入本地 smoke 回归。 |

## 行为

- `is_available()`：
  - 要求 Team Cloud URL、成员级 token 或等价可信凭据，以及完整 `TeamContext`。
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
  - 当前 GA 主路径暴露 `team_memory_search`、`team_memory_add`、`team_memory_propose`、`team_memory_promote`、`team_memory_forget`。
  - `team_memory_add` 用于显式新增 active 团队记忆。
  - `team_memory_propose` 保留为待审核候选。
- `system_prompt_block()`：
  - 在 Team Cloud active 时提示模型：用户明确要求新增团队记忆时必须调用 `team_memory_add`，不要落到本地 `memory` 工具。

## 政策处理

原 P2 runtime plan 写有“新增 `plugins/memory/team_cloud/`”。该条与当前 AGENTS 政策冲突：新 memory backend 不能新增 in-tree provider 目录，应作为 standalone plugin 发布。本步骤保留 provider 核心实现并避免新增 in-tree plugin 目录；后续 standalone plugin 可 import 该核心实现或复制该契约。

## 非目标

- 不注册 memory plugin。
- 不在 `plugins/memory/` 新增 in-tree provider 目录。
- 不实现 Go 服务端 extraction worker；Go 版当前只保存 observation，自动生成可见 memory item 需要后续 worker/离线任务消费。

## 后续衔接

- P2-12：在 provider core 上补齐 memory tool schemas 和 handler routing。
- P2-13：补齐 `/v1/memory/observations` API 与 turn metadata/context fencing。
- P2-14：将 `team_context` 从 AIAgent 初始化透传给 memory provider。
