# P0-02 Hermes 代码边界审计

日期：2026-05-22
状态：Audited for P0 execution
前置：`P0-01 GA 范围冻结`

## 审计结论

企业版团队功能应以新增 Team Cloud 控制面和显式 runtime 上下文为主，Hermes core 只做必要的透传、hook 扩展和 runtime provider 接入。现有代码已经有可复用边界：`AIAgent` 构造链、`MemoryProvider` 生命周期、Gateway `SessionSource`、API Server agent 创建、plugin `pre_tool_call` 阻断 hook。P1-P3 不应把 Casdoor/SpiceDB/PostgreSQL/MinIO 业务逻辑直接塞进 `run_agent.py` 或平台 adapter。

## 必改边界清单

| 区域 | 当前入口 | 必须改动 | 不应改动 |
| --- | --- | --- | --- |
| `run_agent.py` | `AIAgent.__init__` 是薄封装，转调 `agent.agent_init.init_agent`；已有 `platform/user_id/chat_id/gateway_session_key` 参数 | 增加 `team_context` 可选参数并转发；保持默认 `None` 向后兼容；在 session/activity/audit 元数据中暴露只读快照 | 不在 `run_conversation()` 内直接调用 Team Cloud 或 SpiceDB |
| `agent/agent_init.py` | `init_agent()` 负责保存构造参数、加载 memory provider，并把 gateway 身份放入 `_init_kwargs` | 保存 `agent.team_context`；将 `team_context`、`org_id/team_id/project_id/member_id/actor_type` 透传给 memory provider 和 tool/audit helper；补兼容测试 | 不把 Team Cloud HTTP client 初始化成全局单例 |
| `agent/conversation_loop.py` | turn start 调 `memory_manager.on_turn_start()`，prefetch 只执行一次，并把结果作为 ephemeral user context 注入 | 保持现有 prefetch 注入位置；只让 TeamMemoryProvider 通过 `prefetch()` 返回 Personal/Team Shared 两段 fenced context | 不把 recalled memory 写入持久 transcript |
| `agent/memory_provider.py` / `agent/memory_manager.py` | Provider 支持 `initialize(session_id, **kwargs)`、`prefetch()`、`sync_turn()`、tools、session hooks；manager 当前限制一个外部 provider | 定义 TeamMemoryProvider 需要的 kwargs 合约；确认团队记忆 provider 是否作为唯一企业 provider 启用；为 `session_id`、`team_context` 增加测试 | 不新增 `plugins/memory/<provider>` 目录，除非先修改“无新增 in-tree memory provider”政策 |
| `plugins/memory/__init__.py` | 只从 bundled `plugins/memory/` 和 `$HERMES_HOME/plugins/` 载入 active provider | 若 TeamMemoryProvider 作为 repo 内企业组件，需要新增受控加载路径或让 Team Cloud 安装为用户/独立插件 | 不绕过 active `memory.provider` 配置加载多个外部 provider |
| `agent/tool_executor.py` | 执行前调用 `get_pre_tool_call_block_message()`，registry 工具再调用 `model_tools.handle_function_call(skip_pre_tool_call_hook=True)` | 给 pre hook 传入 `session_id/tool_call_id/team_context/platform/user_id`；保证 memory provider tools 和 agent-loop tools 也走同一团队工具策略 | 不只在 `model_tools.handle_function_call()` 做策略检查，否则 memory/provider/agent-loop 工具会绕过 |
| `model_tools.py` | registry 工具支持 `pre_tool_call` 阻断、`post_tool_call` 观察、`transform_tool_result` | 为 post hook 增加执行状态、错误标记、team context、decision id，支撑 `cloud_tool_calls` 和 audit | 不把具体 TeamToolPolicyHook 写死在 dispatcher |
| `hermes_cli/plugins.py` | `VALID_HOOKS` 已有 `pre_tool_call`、`post_tool_call`、approval hooks、`pre_gateway_dispatch` | 扩展 hook kwargs 文档和测试；允许 `pre_tool_call` 返回 block message 作为 fail closed 策略载体 | 不改变现有 observer-only hook 的默认 fail-open 兼容行为 |
| `gateway/session.py` | `SessionSource` 保存 platform/chat/user/thread/guild 等来源 | 增加或旁路保存 Team identity：`org_id/team_id/project_id/member_id/external_identity_id/actor_type/auth_method` | 不把平台 user_id 直接当 Team Cloud member_id |
| `gateway/platforms/base.py` | `MessageEvent` 是 adapter 统一事件结构 | 增加可选 `team_context` 或 metadata 字段承载 TeamGatewayIdentityResolver 结果 | 不要求每个平台 adapter 直接认识 Casdoor/SpiceDB |
| `gateway/run.py` | `_is_user_authorized()` 做 allowlist；创建 `AIAgent` 时传 platform/user/chat/session key；busy path 已有授权 gate | 在 allowlist 后增加 TeamGatewayIdentityResolver；创建/复用 agent 时把 team_context 纳入 cache signature；成员禁用需 fail closed 并清理缓存 | 不在单个平台 adapter 中重复实现团队身份绑定 |
| `gateway/platforms/api_server.py` | 当前 Bearer 是单一 API key；`X-Hermes-Session-Key` 只在配置 API key 时允许；`_create_agent()` 不传 user/team identity | 增加 Team Cloud trusted headers 或 PAT/service account 校验；解析 `org/team/project/member` 后传 `team_context`；拒绝未授权 session key/memory scope | 不继续把任意 `X-Hermes-Session-Key` 当企业记忆权限边界 |

## 推荐新增文件

| 文件 | 责任 |
| --- | --- |
| `agent/team_context.py` | 定义 `TeamContext` dataclass、序列化、校验、空上下文 helper |
| `team_cloud/` | Team API、worker、配置、DB migration、auth/authz/memory/backup 模块 |
| `team_cloud/runtime/memory_provider.py` | TeamMemoryProvider 适配 MemoryProvider ABC，内部只调用 Team Cloud API |
| `team_cloud/runtime/tool_policy.py` | TeamToolPolicyHook 逻辑：风险分类、SpiceDB check、approval、audit |
| `gateway/team_identity.py` | Gateway 外部身份绑定解析，输出 TeamContext，不依赖具体平台 adapter |
| `gateway/platforms/api_server_identity.py` | OpenAI-compatible API 的 PAT/service account/trusted header 解析 |
| `tests/team_cloud/` | Team Cloud API、migration、worker、auth/authz 单元和集成测试 |
| `tests/run_agent/test_team_context.py` | `AIAgent.team_context` 透传、memory init、向后兼容 |
| `tests/gateway/test_team_identity.py` | Gateway 绑定、禁用成员、跨 org 拒绝 |
| `tests/gateway/test_api_server_team_headers.py` | API Server identity headers、session key 权限、未授权拒绝 |
| `tests/plugins/test_team_tool_policy_hook.py` | 工具策略 fail closed、高危审批、审计事件 |

## 关键风险

1. `MemoryManager` 目前只允许一个外部 provider。企业双层记忆若实现为 provider，需要决定是否替代当前 `memory.provider`，或通过独立 Team Cloud runtime 包加载。
2. 工具策略不能只挂在 `model_tools.handle_function_call()`，因为 `agent/tool_executor.py` 会直接处理 memory、clarify、delegate、context-engine 和 provider tools。
3. Gateway agent cache 以 `session_key` 和配置签名复用 agent。`team_context` 改变时必须刷新 cache，否则成员禁用、角色变化或项目切换会复用旧权限。
4. API Server 的 `X-Hermes-Session-Key` 是长期 memory scope 辅助标识，不是授权主体。企业模式下必须由 Team Cloud 验证主体和 scope 后再注入。
5. `pre_tool_call` hook 当前阻断语义足够，但 observer hook 失败会被吞掉。TeamToolPolicyHook 必须在策略客户端不可用时明确返回 block，而不是依赖异常传播。

## 分阶段落点

| 阶段 | 落点 |
| --- | --- |
| P1 | 新建 `team_cloud/` 骨架、配置、health、auth/authz client shell；不接入 agent 主路径 |
| P2 | 加 `TeamContext`、TeamMemoryProvider、API/Gateway identity 透传、双层记忆召回和 observations |
| P3 | 加 TeamToolPolicyHook、工具审计、personal backup policy/exporter/restore |
| P4-P5 | 压测、安全测试、部署包、Runbook、最终回归和签字 |

## 审计证据

- `run_agent.py:349`-`484`：`AIAgent.__init__` 参数转发入口。
- `agent/agent_init.py:1034`-`1143`：内置 memory store、外部 memory provider 初始化和工具注入。
- `agent/conversation_loop.py:561`-`580`、`746`-`762`、`4048`-`4053`：memory turn start、prefetch 注入、turn sync。
- `agent/memory_provider.py:60`-`119`、`121`-`137`、`144`-`225`：MemoryProvider lifecycle 和 tool contract。
- `agent/tool_executor.py:125`-`143`、`499`-`515`、`714`-`726`：tool pre-hook 与 provider tool 直连路径。
- `model_tools.py:741`-`889`：registry tool dispatcher、pre/post/transform hook。
- `hermes_cli/plugins.py:128`-`168`、`701`-`716`、`1428`-`1469`：hook 定义、注册和 block 语义。
- `gateway/session.py:70`-`137`、`gateway/platforms/base.py:940`-`992`：Gateway source/event 模型。
- `gateway/run.py:16097`-`16313`：Gateway 创建 `AIAgent` 时的身份透传入口。
- `gateway/platforms/api_server.py:744`-`827`、`851`-`912`：API key、session key 和 API Server agent 创建。
