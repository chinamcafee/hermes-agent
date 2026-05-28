# GTC-68 CLI Team Cloud 记忆运行时自动挂载

日期：2026-05-24
状态：Implemented

## 背景

CLI 已具备 Team Cloud 连接、登录和 `team_context` 注入，但普通交互中显式说“增加团队记忆”时，模型仍可能只使用本地 `memory` 工具。根因是 Team Cloud memory provider 没有在 CLI team mode 下自动挂载到 agent memory runtime，因此 `team_memory_*` 工具不一定出现在模型工具面。

## 决策

- Team Cloud 是 Hermes 的一等团队能力，不再要求用户额外安装 `plugins/memory/team_cloud`。
- 当 `team_cloud.enabled=true`、URL、成员 session token 和 `team_context` 完整时，`AIAgent` 自动创建 `TeamMemoryProvider`。
- `MemoryManager` 允许 first-party `team_cloud` provider 与一个个人外部 memory provider 共存。
- 新增 `team_memory_add`，专门处理用户明确要求新增 active 团队记忆的场景。
- `team_memory_propose` 保留为待审核候选，不再与直接新增 active 记忆混用。

## 行为

显式团队记忆新增：

1. 用户在 Hermes CLI 中说“增加团队记忆”“保存为团队记忆”“新增一条团队记忆”等。
2. provider system prompt 要求模型调用 `team_memory_add`，不能落到本地 `memory` 工具。
3. `team_memory_add` 调用 Team Cloud Go `POST /v1/memory`。
4. payload 固定包含 `scope=team_shared`、`status=active`、`source_type=admin_created`、`created_by_member_id=<当前成员>`。
5. Dashboard “记忆治理”默认 active 列表刷新后应能看到该记忆。

自动 observation：

1. 每个完整、未中断的 agent turn 结束后，`TeamMemoryProvider.sync_turn()` 调用 `/v1/memory/observations`。
2. observation 只代表“可供抽取的会话观察”，不等价于已经创建团队记忆。
3. Go 服务端当前会持久化 observation 为 `pending`；自动生成可见 memory item 仍需要后续 extraction worker 或离线任务消费。

自动加载：

1. 每个 agent turn 开始前，`MemoryManager.prefetch_all()` 调用 `TeamMemoryProvider.prefetch()`。
2. provider 调用 `/v1/memory/prefetch`，带上 org/member/team/project 和 `include_personal`。
3. 返回的 personal 与 team_shared 记忆会被注入 `<memory-context>`，作为模型可参考的运行时上下文。

## 验证

- `tests/run_agent/test_memory_provider_init.py::test_aiagent_auto_activates_team_cloud_memory_provider_for_cli_team_mode`
- `tests/team_cloud/test_team_memory_provider_tools.py::test_team_memory_add_tool_creates_active_team_memory_via_team_cloud`
- `tests/team_cloud/test_team_memory_provider_tools.py::test_team_memory_provider_system_prompt_routes_explicit_team_memory_adds`

