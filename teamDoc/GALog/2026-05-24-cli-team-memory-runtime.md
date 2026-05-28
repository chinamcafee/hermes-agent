# 2026-05-24 CLI Team Cloud 记忆运行时自动挂载

## 问题

用户在 Hermes CLI 交互中明确说“增加团队记忆”后，CLI 返回新增成功，但 Team Cloud Dashboard “记忆治理”刷新后看不到对应记录。

## 根因

- CLI 只把 `team_context` 传入 `AIAgent`，但没有在 team mode 下自动挂载 `TeamMemoryProvider`。
- 在未挂载 provider 时，模型工具面没有 `team_memory_*` 工具，只能使用本地 `memory` 工具或自然语言回应。
- `team_memory_propose` 语义是提交候选，服务端默认会创建 `pending_review`，不适合作为“明确新增 active 团队记忆”的工具。

## 改动

- `agent/agent_init.py`：team mode 下自动创建并初始化 `TeamMemoryProvider`。
- `agent/memory_manager.py`：允许 first-party `team_cloud` provider 与一个个人外部 provider 共存。
- `team_cloud/memory/provider.py`：新增 `team_memory_add` 工具和 system prompt routing。
- `tests/run_agent/test_memory_provider_init.py`：覆盖 CLI team mode 自动挂载和工具注入。
- `tests/team_cloud/test_team_memory_provider_tools.py`：覆盖 `team_memory_add` payload、工具列表和提示词。
- `teamDoc`：记录显式新增、自动 observation、自动抽取和 prefetch 加载边界。

## 结论

显式“增加团队记忆”现在应调用 Team Cloud Go `POST /v1/memory`，并创建 Dashboard active 列表可见的 `team_shared` 记忆。自动抽取不是这条直接新增链路；当前 Go 服务端只持久化 observation，后续需要 extraction worker 消费后才会生成自动抽取记忆。

