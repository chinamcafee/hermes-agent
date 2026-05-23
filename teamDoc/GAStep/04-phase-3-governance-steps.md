# 04. Phase 3：数据治理、备份恢复和权限硬化

## 1. 工具权限

1. 建立工具风险表：safe_read、network、file_read、file_write、terminal、destructive、secret。
2. 每个 Hermes tool 映射风险等级。
3. 新增 `plugins/team_policy/`。
4. 在 `pre_tool_call` 中读取 actor、tool、args、session、platform。
5. 调 SpiceDB 检查 `tool.execute`。
6. 对高危工具触发 Hermes approval。
7. 写 `cloud_tool_calls` 和 audit。
8. 对 block 和 approval timeout 做明确错误返回。

## 2. 个人记忆备份

1. 创建 `backup_policies`、`backup_jobs`、`restore_jobs`。
2. Web Personal Memory 页面加入 backup policy 设置。
3. 导出 personal memory JSONL。
4. 生成 manifest。
5. 加密备份包。
6. 计算 checksum。
7. 上传 MinIO。
8. 写 object manifest。
9. 发送成功/失败通知。
10. 支持 backup retention cleanup。

## 3. 恢复流程

1. 成员选择备份包。
2. 后端下载并校验 checksum。
3. 解密到 restore staging。
4. 生成 restore preview。
5. 标出新增、跳过、冲突、覆盖。
6. 用户选择策略：merge、overwrite、archive-old。
7. 写入 `restore_jobs`。
8. 执行恢复。
9. 重建 embedding。
10. 写 memory_events 和 audit。

## 4. 组织导出和删除

1. 定义 org export manifest。
2. 导出 org/team/project/member metadata。
3. 导出 sessions/messages/tool calls。
4. 导出 memory_items/memory_events。
5. 导出 SpiceDB relationships snapshot。
6. 上传 MinIO org exports。
7. 数据删除请求支持 member/project/org。
8. 删除前可选 export then delete。
9. hard delete worker 清 PostgreSQL、SpiceDB、MinIO。
10. 删除完成写 final audit。

## 5. Break-glass

1. 定义 break-glass request 表。
2. Owner 发起，Security Admin 审批，或反向组合。
3. 设置原因、工单、时间窗口、资源范围。
4. 写短期 SpiceDB relationship。
5. 到期自动撤销。
6. 所有读取写 audit。
7. 通知被访问成员，除非策略设置延迟通知。

## 6. 审计和权限解释

1. Audit 页面支持 actor/action/resource/decision/time 过滤。
2. 敏感读取和高危工具单独视图。
3. Permission Explorer 显示 SpiceDB check 输入和结果。
4. 显示 relationship 路径和最近变更。
5. 支持导出 audit。
6. 对 outbox lag、dead letter、permission deny spike 告警。

## Phase 3 出口标准

- Guest 无法执行 terminal/file write。
- Developer 执行 terminal 需要审批。
- personal backup 可生成、下载、恢复、删除。
- checksum mismatch 阻止恢复。
- 组织导出可在空环境回灌核心数据。
- break-glass 全链路可审计。

