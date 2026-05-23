# 01. 需求拆解与缺口分析

## 1. 目标需求拆解

用户需求可以拆成 5 个产品能力域。

新增约束：所有新引入组件必须源码可访问，可以自研或采用开源/源码可访问项目；闭源商业服务不能成为团队身份、权限、记忆或云端数据管理的必需依赖。本轮 GA 方案限定为 Casdoor + SpiceDB + PostgreSQL/pgvector + MinIO。

### A. 团队成员共同使用

需要：

- 组织/团队/项目模型。
- 成员邀请、加入、退出、禁用。
- 多入口：Web、API、Telegram、Slack、Discord、Feishu 等。
- 同一成员跨平台身份绑定。
- 团队级默认模型、工具、工作目录、预算策略。
- 群聊和线程上下文共享。

Hermes 现状：

- Gateway 已有多平台和平台用户 ID。
- Session key 已能区分 DM、group、thread、per-user/shared。
- 没有组织/成员体系。

缺口：

- `org_id`、`team_id`、`member_id`、`external_identity` 统一模型。
- Casdoor OIDC 登录态、API token、service account 多用户化。
- 平台身份绑定流程。
- Casdoor user/group 到 Team Cloud member/team 的同步流程。
- SpiceDB relationship 写入和权限解释。

### B. 长期记忆云同步

需要：

- 云端 memory store。
- 自动抽取、去重、召回、更新、遗忘。
- 多设备、多平台共享。
- 离线/失败重试。
- 数据导入导出。

Hermes 现状：

- MemoryProvider 生命周期完整。
- 多个外部 provider 支持云端或自托管。
- RetainDB provider 有 SQLite write-behind queue 示例。

缺口：

- 没有 Hermes 原生 Team Cloud 记忆服务。
- 没有统一的团队记忆 schema、审计、权限、生命周期。
- 外部 provider 的 filters/container 不等于产品级权限边界。

### C. 个人记忆和团队共同记忆两级分类

需要：

- 个人记忆：只对本人和有权限管理员可见。
- 团队共同记忆：团队成员共享，可被审核、归档、删除。
- 自动召回时明确分区，防止泄露。
- 明确的写入策略：哪些内容自动进入个人记忆，哪些需要审核后进入团队记忆。

Hermes 现状：

- Provider 可拿到 `user_id` 和 `chat_id`。
- 部分 provider 的 container、user filter 或 bank template 可模拟 scope，但只有通过源码和许可证审查后才能作为可选适配器。

缺口：

- 缺少一等 `memory_scope`。
- 缺少共享记忆的审批/提升流程。
- 缺少 per-memory ACL。
- 缺少跨 scope ranking 和注入格式。

### D. 丰富团队帐号权限管理

需要：

- 组织 Owner/Admin/Member/Guest/Service Account。
- 自定义角色和权限。
- 资源级授权：会话、记忆、文档、工具、连接器、API key。
- 平台命令权限和工具执行权限。
- 审计、权限解释、最小权限默认值。

Hermes 现状：

- Gateway slash command access policy。
- API server 单 Bearer key。
- Dashboard ephemeral token。
- Tool approval 和 `pre_tool_call` hook 可作为权限拦截基础。

缺口：

- 没有登录、组织、成员、角色、权限引擎。
- 没有 per-tool/per-resource 权限。
- 没有 service account 和 token scope。
- 没有审计事件标准。

### E. 云端数据管理

需要：

- 管理会话、记忆、文档、连接器、成员、API keys、审计日志。
- 搜索、过滤、导出、删除、保留策略。
- 敏感数据检测和脱敏。
- 数据迁移和备份恢复。

Hermes 现状：

- Dashboard 本地管理 sessions/config/env/logs/cron/skills。
- SessionDB 本地可查询。
- Plugins dashboard 可扩展。

缺口：

- Dashboard 不是多用户云控制台。
- SQLite 不适合作为团队云数据源。
- 数据治理能力需要新建。

## 2. 缺口矩阵

| 需求 | Hermes 可复用 | 需要二次开发 | 复杂度 |
| --- | --- | --- | --- |
| 多平台团队聊天 | Gateway、SessionStore、platform adapters | 组织身份映射、团队配置、统一成员模型 | 中 |
| Web 团队入口 | Dashboard React 组件可参考，API Server 可参考 | 多用户 Web app、登录、会话、权限 | 高 |
| API 团队入口 | API Server OpenAI-compatible | JWT/API key scope、user/team header、rate limit | 中 |
| 个人记忆 | MemoryProvider、user_id 透传、provider filter 可作适配参考 | personal scope schema、权限、召回策略 | 中 |
| 团队共同记忆 | Provider tools、on_memory_write | shared scope、审批、promotion、ACL、审计 | 高 |
| 云同步 | 外部 provider、RetainDB queue 示例 | Team Cloud 存储、worker、重试、冲突处理 | 高 |
| 身份认证 | Gateway platform identity、API Bearer key | Casdoor OIDC/SAML/SCIM、成员同步、服务账号 | 高 |
| 资源权限 | slash_access、approval hook | SpiceDB schema、relationship outbox、permission explorer、tool policy | 高 |
| 云数据管理 | Dashboard pages 可参考 | SaaS admin console、export/delete/retention/audit | 高 |
| 安全合规 | 现有本地安全约束和 approval | tenant isolation、encryption、audit、DPA/GDPR | 高 |

## 3. 最小可行边界

如果只做内部技术验证：

- 使用现有 Gateway 或 API Server。
- 只支持一个或两个团队入口，例如 Web + Telegram。
- 用最小 `TeamMemoryProvider + PostgreSQL/pgvector` 实现个人/团队记忆。
- 身份和权限仍按 Casdoor + SpiceDB 搭建，不能用临时数据库 ACL 替代最终模型。
- 权限只做 Owner/Admin/Member 三档。
- 不做完整云端数据管理，只做记忆列表、删除、导出。

如果要成为 GA “开箱即用团队版”：

- 必须新增 Team Cloud。
- 必须新增 Casdoor 身份接入和 SpiceDB 资源权限模型。
- 必须新增 `TeamMemoryProvider`。
- 必须新增 PostgreSQL/pgvector canonical memory 和 MinIO 个人备份。
- 必须新增管理控制台、审计、备份恢复、导出删除、升级迁移和 Runbook，而不是把本地 Dashboard 直接暴露出去。
