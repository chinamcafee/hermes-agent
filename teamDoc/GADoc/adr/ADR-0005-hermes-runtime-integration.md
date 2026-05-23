# ADR-0005：通过 TeamContext 和 runtime hooks 集成 Hermes

状态：Accepted
日期：2026-05-22
适用阶段：P1-P5

## 背景

Hermes 已有成熟的 Agent loop、Gateway、OpenAI-compatible API、tool registry、memory provider 和 plugin hook。企业版需要把 Team Cloud 的身份、权限、双层记忆、工具治理和审计注入 runtime，但不应让 Hermes core 直接承担 Casdoor、SpiceDB、PostgreSQL 或 MinIO 的业务边界。

## 决策

采用 Team Runtime Adapter 集成方式：

```text
Team API / Gateway / API Server
  -> resolve TeamContext
  -> SpiceDB check chat.run
  -> create AIAgent(team_context=...)
  -> TeamMemoryProvider.prefetch()
  -> TeamToolPolicyHook.pre_tool_call()
  -> stream response/events
  -> TeamMemoryProvider.sync_turn()
```

Hermes core 只新增必要稳定接口：

- `AIAgent.__init__(team_context=None)` 并转发到 `agent.agent_init.init_agent()`。
- `agent.team_context` 作为只读 runtime 快照。
- MemoryProvider `initialize()` 接收 `team_context`。
- Gateway/API Server 在创建 agent 前解析可信身份并传入 `team_context`。
- plugin `pre_tool_call` / `post_tool_call` hook 获得 `team_context`、`platform`、`user_id`、`session_id`、`tool_call_id` 等参数。

## 备选

| 方案 | 结果 |
| --- | --- |
| 在 `run_agent.py` 中直接调用 Team Cloud | 短期快，但会把企业权限边界硬编码进 core，难以测试和复用 |
| 只做外部 wrapper，不改 Hermes | 无法覆盖 memory provider、tool hook、Gateway/API identity 和 runtime event bridge |
| 每个平台 adapter 单独集成团队身份 | 重复逻辑多，禁用传播、缓存和审计容易不一致 |

## 后果

- P2 必须补 `TeamContext` 向后兼容测试，默认 `None` 不改变 CLI 和旧 Gateway 行为。
- Gateway agent cache signature 必须包含 team context 关键字段。
- API Server 不能信任任意 session key 或 header，必须只接受 Team Cloud trusted headers、PAT 或 service account 解析结果。
- 工具策略必须在 `agent/tool_executor.py` 的 pre-hook 层统一执行，覆盖 registry tools、provider tools 和 agent-loop tools。
- TeamMemoryProvider 只调用 Team Cloud API，不直接读写 PostgreSQL/MinIO/SpiceDB。

## 回滚条件

如果 TeamContext 透传导致旧 CLI/Gateway/API 行为回归，必须回滚到默认 `None` 完全 no-op，并保留 Team Cloud 外部入口。不得回滚到 prompt-only 权限、平台 allowlist 或本地 memory provider 过滤作为企业隔离方案。
