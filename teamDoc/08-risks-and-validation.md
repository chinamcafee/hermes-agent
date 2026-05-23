# 08. 风险与 GA 验证计划

GA 验收的核心标准是：Casdoor 身份可信、SpiceDB 权限正确、PostgreSQL/pgvector 记忆不串租户、MinIO 备份可恢复、Hermes 工具不能绕过团队策略。

## 1. 最大风险：个人记忆泄露

风险：

- A 的 personal memory 被注入给 B。
- 管理员绕过 break-glass 读取成员个人记忆。
- 个人备份包被其他成员下载。

控制：

- personal memory SQL 强制 `subject_member_id = current_member_id`。
- SpiceDB `memory.read_personal` 只授予 owner。
- MinIO object manifest 绑定 owner，下载前 check `backup.read`。
- break-glass 需要双人审批、时间窗口、通知和审计。

验收：

- 跨成员 personal memory 测试 100% deny。
- personal backup 跨成员下载测试 100% deny。
- 所有 break-glass 访问都有 audit 和审批记录。

## 2. 团队共享记忆串租户

风险：

- 不同 org 使用相同 team/project 名称导致召回串租户。
- pgvector 检索先向量后过滤导致候选泄露。
- SpiceDB relationship 延迟同步导致错误 allow。

控制：

- 所有表和索引查询强制 `org_id`。
- pgvector 查询包含 SQL metadata filter。
- 查询后批量 SpiceDB check。
- relationship outbox 未完成时危险操作 fail closed。

验收：

- 构造同关键词跨 org/team 记忆，召回 0 泄漏。
- SpiceDB 不可用时默认拒绝管理和高危读写。
- Outbox dead letter 会阻止相关资源发布。

## 3. Casdoor 集成错误

风险：

- JWT issuer/audience 校验不严。
- JWKS rotation 后 token 校验失败。
- Casdoor 用户禁用后 Team Cloud 仍允许访问。
- 外部 IdP group 同步延迟导致权限未收回。

控制：

- 完整校验 issuer、audience、signature、exp、nbf、nonce。
- JWKS cache 支持刷新和 fallback。
- 每次请求检查 member status。
- Casdoor webhook/SCIM/periodic reconcile 三重同步。

验收：

- 伪造 JWT、过期 JWT、错误 audience 全部拒绝。
- 禁用用户 60 秒内失去 Team Cloud 访问。
- Casdoor group 变更能同步 SpiceDB relationship。

## 4. SpiceDB 模型错误

风险：

- schema 表达错误导致过度授权。
- relationship 写入丢失。
- permission lookup 与列表 API 不一致。

控制：

- SpiceDB schema 纳入代码评审和 CI。
- 每个 permission 都有正反测试。
- PostgreSQL outbox 幂等写 SpiceDB。
- 列表 API 必须经过 lookup/check 过滤。

验收：

- 权限矩阵测试覆盖 Owner/Admin/Curator/Developer/Member/Guest/Service Account。
- schema 变更必须带 migration 和回滚。
- permission explorer 能解释关键 allow/deny。

## 5. 工具权限绕过

风险：

- 模型通过 terminal/file tool 绕过团队权限。
- Gateway slash command 允许但 tool permission 未检查。
- Service account 用宽 token 执行高危工具。

控制：

- `TeamToolPolicyHook` 是所有工具调用的中央拦截点。
- 高危工具要求 SpiceDB allow + Hermes approval。
- 文件工具有 workspace allowlist。
- Service account token 有 scope、过期、IP allowlist。

验收：

- Guest 无法读写文件或执行 terminal。
- Member 无法执行 destructive tool。
- Developer 执行 terminal 需要审批。
- 所有 block/approval 都有 audit。

## 6. MinIO 备份不可恢复

风险：

- 备份对象缺 manifest 或 checksum mismatch。
- 用户恢复覆盖新记忆。
- MinIO 对象生命周期误删有效备份。

控制：

- 每个对象必须有 `object_manifests`。
- 备份包加密、checksum、版本化。
- 恢复先 preview，再 staging，再用户确认。
- 生命周期策略只处理超出 retention 的对象。

验收：

- 随机抽样个人备份恢复成功。
- checksum mismatch 会阻止恢复并告警。
- 删除个人备份不会删除其他成员对象。

## 7. 性能与可用性

风险：

- 每 turn 同时调用 pgvector 和 SpiceDB 导致首 token 延迟高。
- SpiceDB check 量过大。
- Review queue 和 backup queue 积压。

控制：

- prefetch top-k 和候选上限。
- 批量 SpiceDB check。
- 短期 permission cache，cache key 含 revision/subject/resource。
- worker 分队列：memory extraction、embedding、backup、outbox。

验收：

- memory prefetch P95 <= 500ms。
- SpiceDB check P95 <= 30ms，批量 P95 <= 100ms。
- worker lag 有 dashboard 和告警。

## 8. GA 测试矩阵

单元测试：

- Casdoor JWT validation。
- SpiceDB schema permission tests。
- memory scope SQL filters。
- MinIO manifest/checksum。
- TeamMemoryProvider JSON tool contract。

集成测试：

- Web login -> chat -> personal memory write -> backup -> restore。
- Gateway bind -> group chat -> team_shared proposal -> review -> recall。
- Service account -> API run -> limited tool permission。
- Casdoor disable user -> immediate access deny。
- SpiceDB outage -> fail closed。

安全测试：

- Header spoofing。
- Token replay。
- Prompt injection 读取 personal memory。
- Cross-tenant vector search。
- Tool permission bypass。
- Break-glass abuse。

运维测试：

- PostgreSQL PITR。
- SpiceDB relationship snapshot restore。
- MinIO bucket restore。
- Casdoor config restore。
- Rolling upgrade and rollback。

## 9. GA 出口标准

- P0/P1 安全缺陷为 0。
- 权限矩阵正反用例 100% 通过。
- 备份恢复演练 100% 通过。
- 3 个试点团队连续 2 周无数据泄露和阻塞故障。
- 安装、升级、备份、恢复、权限排查都有 Runbook。
- 所有源码可访问组件有版本、许可证、镜像来源和 SBOM。
