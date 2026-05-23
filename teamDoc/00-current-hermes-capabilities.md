# 00. Hermes 现有能力盘点

本盘点在新增约束下解读现有能力：团队版新引入组件必须源码可访问、自托管或可替换；闭源商业服务不能作为身份、权限、记忆或云端数据管理的必需依赖。本轮 GA 目标架构限定为 Casdoor + SpiceDB + PostgreSQL/pgvector + MinIO。

## 1. Agent Runtime 已支持平台身份透传

`AIAgent.__init__` 已经接受以下与团队场景相关的字段：

- `platform`
- `session_id`
- `user_id`
- `user_name`
- `chat_id`
- `chat_name`
- `chat_type`
- `thread_id`
- `gateway_session_key`
- `credential_pool`

Gateway 创建 Agent 时，会把平台用户和会话信息传入：

- `gateway/run.py` 创建 `AIAgent(...)` 时传入 `source.user_id`、`source.user_name`、`source.chat_id`、`source.chat_name`、`source.chat_type`、`source.thread_id`、`session_key`。
- `agent/agent_init.py` 初始化 memory provider 时也会把这些字段放入 `_init_kwargs`。

这意味着团队成员身份不需要从零接入到 Agent 内核；关键缺口是缺少统一的 `organization_id/team_id/member_id/role` 语义，以及这些身份如何绑定到 Telegram/Slack/Discord/Web/API 用户。

## 2. Gateway 已经能支撑多人使用

现有 Gateway 支持 Telegram、Discord、Slack、WhatsApp、Feishu、WeCom、Matrix、Mattermost、Email、SMS、API Server、Webhook 等平台。

已有能力：

- 平台 allowlist，例如 `allow_from`、`group_allow_from`。
- DM Pairing 教程和 pairing 命令，适合内部团队快速加人。
- Slash command gating：`allow_admin_from`、`user_allowed_commands`、`group_allow_admin_from`、`group_user_allowed_commands`。
- 群聊/线程 session key 规则：`gateway/session.py::build_session_key()` 支持 DM、group、thread、per-user 或 shared session。
- 多用户共享会话提示：`shared_multi_user_session` 会让 system prompt 避免把会话固定到单一用户。

限制：

- 这些是平台级 ACL，不是团队帐号系统。
- 角色只覆盖 slash command，不覆盖工具、记忆、会话、文档、API token、管理操作。
- 没有组织、团队、项目、成员表。
- 没有统一审计日志或权限解释。

## 3. SessionDB 已经有本地会话存储，但不是云端多租户数据层

`hermes_state.py` 的 `sessions` 表已有：

- `id`
- `source`
- `user_id`
- `model`
- token/cost 统计
- `title`
- `parent_session_id`

`messages` 表存储会话消息、工具调用、reasoning 等。

适合复用的点：

- 本地历史、Dashboard 会话浏览、FTS5 搜索。
- 迁移工具可以读取 SessionDB，把旧会话导入 Team Cloud。

不足：

- 无 `org_id/team_id/project_id`。
- SQLite 本地单实例，不适合云端多租户。
- 没有资源级权限。
- 删除、导出、保留策略、审计不完整。

## 4. 记忆系统已有 provider 插件架构

`agent/memory_provider.py` 定义了 MemoryProvider 生命周期：

- `initialize(session_id, **kwargs)`
- `system_prompt_block()`
- `prefetch(query)`
- `queue_prefetch(query)`
- `sync_turn(user, assistant)`
- `get_tool_schemas()`
- `handle_tool_call()`
- `on_session_end()`
- `on_pre_compress()`
- `on_memory_write()`
- `on_delegation()`

`agent/memory_manager.py` 负责汇总 prompt、prefetch、sync、tool routing。重要限制是：

- 内置记忆可和外部 provider 同时存在。
- 外部 provider 只能激活一个。

这对团队版反而是好事：团队版记忆应以一个新的 `TeamMemoryProvider` 形态接入，内部再决定是否调用通过源码/许可证审查的外部 provider，而不是在 Hermes 同时启用多个外部 provider。

## 5. Hermes 生态已有多个记忆 provider

当前文档和代码中可用的 provider：

| Provider | 适合复用的点 | 团队版限制 |
| --- | --- | --- |
| Honcho | workspace/peer/session 建模，用户画像和 AI peer 表征很强 | 不等同于团队共享知识库；权限/数据管理需要外部系统；进入默认架构前需源码和许可证审查 |
| Mem0 | 事实抽取、`user_id`/`agent_id` 过滤、快速集成 | 个人/团队双 scope 需要自定义封装；权限边界不应只靠 provider filters；只可作为可选适配器 |
| Supermemory | `container_tag`、profile、conversation ingest、多容器手动工具 | 自动写入只走 primary container；团队共同记忆需要额外策略；托管闭源形态不能作为必需依赖 |
| RetainDB | provider 里已有 project、user_id、shared file scope 线索 | 生态成熟度和权限能力需再验证；不能直接替代团队控制面 |
| Hindsight | bank template 支持 profile/workspace/user/session | 更偏知识图谱/召回；团队权限要外接 |
| OpenViking | tenant/account header、层级知识库 | 更适合自托管知识库，不是完整团队帐号系统 |
| ByteRover/Holographic | 本地优先 | 不满足云同步和团队共享的核心诉求 |

结论：第三方 provider 只能作为兼容参考或局部增强；GA 核心记忆模型必须自研，并以 PostgreSQL/pgvector 中的 `memory_items` 作为 canonical memory。

## 6. Dashboard 与 API Server 可复用但不能直接当团队云产品

Dashboard：

- FastAPI + React/Vite。
- 有本地配置、环境变量、会话、日志、分析、Cron、Skills、Plugins 页面。
- 有 dashboard plugin 扩展点，后端插件可挂载 FastAPI router。
- 认证是每次启动生成的本地 ephemeral session token。

限制：

- 默认面向 localhost 单用户。
- 文档也说明 Dashboard 没有自身的长期认证，绑定非本地地址有风险。
- 不适合作为多人团队 SaaS 管理台的权限基础。

API Server：

- OpenAI-compatible `/v1/chat/completions`、`/v1/responses`。
- Bearer token 单 key。
- 支持 `X-Hermes-Session-Id` 和 `X-Hermes-Session-Key`。

限制：

- `_create_agent()` 目前没有从 HTTP 请求解析 `user_id/team_id/org_id` 并传给 Agent。
- 单 API key 不能表达成员、角色、scope。
- 适合做早期入口和兼容入口，不适合长期作为团队权限边界；GA 需要由 Team Cloud 校验 Casdoor token 并执行 SpiceDB 权限检查。

## 7. 插件系统适合承载团队版集成

可复用机制：

- 一般插件可注册工具、hook、CLI subcommand。
- Memory provider 插件可注册新 memory provider。
- Dashboard plugin 可扩展本地管理 UI。
- `pre_tool_call` hook 可做工具权限阻断。
- Gateway command registry 和 slash access 已有统一分发。

建议：

- 初期不要硬改 `run_agent.py` 和 `cli.py`。
- 新增 `plugins/memory/team_cloud/` 或独立安装插件，作为团队云记忆入口。
- 新增 Team Cloud SDK/HTTP client。
- 在 Gateway/API Server 加少量 identity propagation patch。
- 需要进入 core 的只放通用扩展点，例如 `team_context`、`request_identity`、`tool_policy_context`。
