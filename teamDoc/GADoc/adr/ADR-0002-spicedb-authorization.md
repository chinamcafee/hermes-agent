# ADR-0002：使用 SpiceDB 作为默认资源级授权系统

状态：Accepted
日期：2026-05-22
适用阶段：P1-P5

## 背景

GA 版本必须隔离组织、团队、项目、成员、会话、个人记忆、团队共享记忆、文档、备份和工具调用。权限需要支持关系继承、反向查询、权限解释、正反 fixture 和跨入口一致性。数据库 ACL、prompt 约束或平台 allowlist 都无法作为最终业务权限边界。

## 决策

使用 SpiceDB 作为默认资源级授权系统。所有跨成员、跨团队、跨项目、跨记忆读取或工具执行都必须走 `CheckPermission` 或批量 check。Team Cloud 负责把业务事件写入 PostgreSQL 后，通过 outbox 幂等同步 SpiceDB relationship。

权限检查顺序：

1. Casdoor/Team Cloud 解析 actor。
2. PostgreSQL 用 `org_id`、scope、status、candidate resource 做粗过滤。
3. SpiceDB 做精确资源权限 check。
4. 危险操作在 relationship 未同步或 SpiceDB 不可用时 fail closed。
5. 敏感读取、删除和权限变更使用更强一致性。

## 备选

| 方案 | 结果 |
| --- | --- |
| 数据库 RLS / ACL 作为唯一授权 | 事务内过滤强，但难以表达跨资源关系、权限解释和跨系统工具授权 |
| OpenFGA | 语义接近，但本轮方案指定 SpiceDB；引入会导致 schema、SDK、CI fixture 分裂 |
| prompt 或 slash command 限制工具 | 不能作为安全边界，模型输出和直接工具路径都可能绕过 |

## 后果

- P0-07 必须产出 organization/team/project/session/memory/document/tool/backup 的 `schema.zed`。
- P1 必须实现 SpiceDB client、relationship outbox、dead letter、authz middleware 和 schema CI。
- P2 memory prefetch 必须先取候选，再批量 SpiceDB check。
- P3 TeamToolPolicyHook 必须基于 SpiceDB decision gate 工具执行。
- 需要监控 check latency、deny/error、outbox lag 和 consistency risk。

## 回滚条件

只有当 SpiceDB 无法在目标部署模式达到可用性、延迟或运维要求，且存在通过 P0 架构评审的 ReBAC 替代引擎时，才允许回滚。回滚不能降级为数据库 ACL、prompt 规则或平台 allowlist。
