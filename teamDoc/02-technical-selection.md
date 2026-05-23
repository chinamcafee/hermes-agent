# 02. 指定技术选型

## 1. 总体原则

团队版 Hermes 的 GA 目标是“权限正确、数据可治理、部署可复制”的 Agent 产品。选型不再围绕最快 PoC，而是围绕 GA 的安全边界、运维边界和可审计边界。

选型原则：

1. 身份认证和资源授权必须拆分：Casdoor 管认证和身份生命周期，SpiceDB 管业务资源权限。
2. 个人记忆和团队共同记忆必须是 PostgreSQL 中的一等数据模型，不依赖 provider filter。
3. 所有用户可见和权限相关数据都有 canonical record、审计事件、导出和删除路径。
4. 所有新组件源码可访问，不引入仅闭源商业服务作为核心依赖。
5. Hermes core 尽量保持 runtime 角色，通过 provider、hook、Gateway bridge 和少量 identity propagation patch 集成。

## 2. 身份认证：Casdoor

Casdoor 是本方案唯一默认身份认证组件。

承担职责：

- 组织用户登录、注册、邀请、禁用、MFA。
- OIDC/OAuth2 token 签发。
- SAML/LDAP/SCIM 等企业身份集成。
- 身份提供商 federation，例如企业 IdP、GitHub、Google、Azure AD。
- 管理用户、组、应用、证书、回调地址和登录策略。

Team Cloud 承担职责：

- 保存产品内 `organization`、`team`、`project`、`member`、`membership`、`external_identity`。
- 把 Casdoor subject 映射为内部 `member_id`。
- 根据 Casdoor webhook、SCIM 或轮询同步成员状态。
- 生成 SpiceDB relationships。
- 处理平台绑定、服务账号、API token scope 和审计。

边界：

- Casdoor 不直接决定某条记忆、某个工具、某个会话是否可访问。
- Casdoor groups/roles 可以作为 Team Cloud 同步输入，但最终业务授权必须落入 SpiceDB。
- Team Cloud 不保存用户密码，不实现登录表单，不绕过 Casdoor token 校验。

## 3. 资源授权：SpiceDB

SpiceDB 是本方案唯一默认资源级授权组件。

承担职责：

- 组织、团队、项目、成员之间的 ReBAC 关系。
- 会话、记忆、文档、备份对象、工具、connector、API token 的资源级权限。
- 权限解释、反向查询和 CI schema 校验。
- 支持 `CheckPermission`、`LookupResources`、`LookupSubjects`、relationship write/delete。

Team Cloud 必须实现授权网关：

```text
AuthzClient.check(actor, permission, resource, context)
AuthzClient.write_relationships(changes, idempotency_key)
AuthzClient.lookup_resources(actor, permission, resource_type)
AuthzClient.explain(actor, permission, resource)
```

设计要求：

- 所有管理 API 先做 Casdoor JWT 校验，再做 SpiceDB permission check。
- 所有 memory prefetch 查询先用 PostgreSQL scope 过滤，再用 SpiceDB 校验资源集合。
- 所有高危工具调用先经过 SpiceDB 的 tool permission，再进入 Hermes approval。
- SpiceDB relationship 写入必须和 PostgreSQL 事务通过 outbox 协调，避免数据和权限不一致。

## 4. 记忆存储：PostgreSQL + pgvector

PostgreSQL 是 canonical data store，pgvector 是默认向量索引。

承担职责：

- `memory_items` 保存个人记忆和团队共同记忆正文、状态、来源、版本、敏感级别。
- `memory_embeddings` 保存 embedding，支持 HNSW/IVFFlat 索引。
- `memory_events` 记录 create/update/read/promote/archive/delete/restore。
- `memory_observations` 作为对话观察队列，供 worker 抽取候选记忆。
- `memory_acl_shadow` 可缓存 SpiceDB 授权快照，仅用于性能优化，不作为最终权限真相。

为什么不引入独立向量库作为默认：

- GA 早期更需要事务一致性、备份恢复和权限过滤正确性。
- PostgreSQL 能同时处理结构化过滤、RLS、审计和向量检索。
- 只有当单租户或全局索引规模超过 pgvector 运维边界，才评估拆分；拆分前 canonical memory 仍留在 PostgreSQL。

## 5. 对象存储和个人备份：MinIO

MinIO 是本方案默认对象存储。

承担职责：

- 成员个人记忆定时备份包。
- 组织级导出包。
- 会话附件、文档原文、导入文件、恢复快照。
- 备份校验 manifest、签名 URL 和生命周期策略。

个人记忆备份原则：

- 默认由成员本人开启、暂停、下载和删除。
- 备份对象加密后写入 MinIO。
- 管理员不能静默读取个人备份；break-glass 必须双人审批并审计。
- 恢复时先进入 staging，用户确认后再覆盖或合并。

许可证注意：

- MinIO 源码可访问，采用 AGPL-3.0。商业化和私有化部署前必须完成法务审查。
- 如果企业客户不接受 AGPL 义务，需要在合同或部署方案中明确替代路径，但本文默认架构仍按用户指定的 MinIO 展开。

## 6. Team Cloud 自研边界

必须自研：

- Go Team API 和 Admin/Data Management API。
- Casdoor token 校验、中间件和成员同步。
- SpiceDB schema、relationship outbox 和授权 SDK。
- PostgreSQL/pgvector 记忆服务。
- MinIO 备份、导出和恢复流程。
- Hermes TeamMemoryProvider。
- TeamToolPolicyHook。
- TeamGateway identity resolver。
- Web Admin Console。

不建议自研：

- 登录认证协议和密码存储。
- ReBAC 引擎。
- 对象存储服务。
- 向量索引底层实现。

实现更新：

- 首次上线部署目标是 `team_cloud_go/` Go 服务端。
- Python `team_cloud/` 从未上线，后续只作为历史参考实现，不再作为生产服务端。
- Go 服务端采用标准库 `net/http`、PostgreSQL repository、单二进制 Docker 镜像和 Kubernetes manifest。
- 生产环境必须设置 `TEAM_CLOUD_DATABASE_URL`；内存后端只允许开发和单元测试使用。

## 7. Hermes 集成方式

GA 推荐采用 Team Runtime Adapter：

```text
Team API
  -> verify Casdoor JWT
  -> resolve member/team/project
  -> SpiceDB check chat.run
  -> create agent_run
  -> start Hermes worker with team_context
  -> TeamMemoryProvider.prefetch()
  -> TeamToolPolicyHook.pre_tool_call()
  -> stream response/events
  -> TeamMemoryProvider.sync_turn()
```

需要进入 Hermes core 的最小改动：

- `AIAgent.__init__` 增加稳定 `team_context` 参数。
- API Server 读取并验证 `X-Hermes-Org-Id`、`X-Hermes-Team-Id`、`X-Hermes-Member-Id` 的可信注入路径。
- Gateway 在创建 Agent 前调用 TeamGateway identity resolver。
- `pre_tool_call` hook 能拿到 actor、resource、session、platform、tool risk。

## 8. 不进入默认路线的组件

在本 GA 框架内，不把以下作为默认方案：

- Keycloak、ZITADEL、Ory：身份方案已限定为 Casdoor。
- OpenFGA：授权方案已限定为 SpiceDB。
- 独立向量库：默认限定为 PostgreSQL + pgvector。
- 第三方 memory SaaS：不能作为 canonical memory 或权限边界。
- 闭源商业身份、权限、向量或记忆服务：不符合源码可访问约束。
