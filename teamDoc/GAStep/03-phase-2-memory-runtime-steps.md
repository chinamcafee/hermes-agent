# 03. Phase 2：双层记忆与 Hermes Runtime 集成

## 1. 数据库与查询层

1. 创建 `memory_items`、`memory_embeddings`、`memory_events`。
2. 创建 `memory_observations`、`memory_review_items`。
3. 为 personal memory 增加 `subject_member_id` 约束。
4. 为 team_shared memory 增加 `team_id/project_id` 约束。
5. 创建 pgvector HNSW 索引。
6. 编写 personal query，只允许 `subject_member_id = current_member_id`。
7. 编写 team query，先按 org/team/project 过滤，再查向量。
8. 对 team query 结果做 SpiceDB batch check。
9. 记录每次召回的 memory IDs。

## 2. Memory API

1. `POST /v1/memory/prefetch`：输入 query、team_context，输出分区记忆块。
2. `GET /v1/memory`：支持 scope/status/type/sensitivity/source 过滤。
3. `POST /v1/memory`：写 personal 或 team candidate。
4. `PATCH /v1/memory/{id}`：版本更新和 diff 事件。
5. `DELETE /v1/memory/{id}`：soft delete，hard delete 交给治理 worker。
6. `POST /v1/memory/{id}/promote`：personal -> team_shared candidate。
7. `GET /v1/memory/review`：团队共享记忆审核队列。
8. `POST /v1/memory/observations`：Hermes turn 观察写入。

## 3. Worker

1. Embedding worker 批处理 pending memory。
2. Extraction worker 消费 conversation observations。
3. Duplicate detector 使用 checksum + semantic similarity。
4. Contradiction detector 把冲突写入 review。
5. PII/secret detector 决定 sensitivity 和是否拒绝写入。
6. Review worker 在 approve 后写 SpiceDB relationship。
7. Worker 失败重试和 dead letter。

## 4. TeamMemoryProvider

1. 新增 `plugins/memory/team_cloud/`。
2. `initialize()` 读取 Team Cloud URL/token 和 `team_context`。
3. `prefetch()` 调 `/v1/memory/prefetch`。
4. `sync_turn()` 调 `/v1/memory/observations`。
5. `get_tool_schemas()` 暴露 search/remember/propose/promote/forget/backup_now。
6. `handle_tool_call()` 写操作前调用 permission check。
7. 返回内容严格为 JSON string。
8. 未配置 Team Cloud 时 fail closed 或 inactive，不污染本地模式。

## 5. Hermes Core 和 Gateway

1. `AIAgent.__init__` 增加 `team_context`，默认 None。
2. `agent/agent_init.py` 将 `team_context` 传给 memory provider。
3. API Server 增加可信 identity headers。
4. API Server 只在 Team Cloud service token 校验后接受 identity headers。
5. Gateway 进入 Agent 前调用 `/v1/external-identities/resolve`。
6. 未绑定平台用户返回绑定提示。
7. session key 增加 org/team 前缀，避免跨团队碰撞。
8. shared group session 禁止注入个人记忆，除非明确 actor context。

## 6. Web Chat 和云会话

1. Team Web Console 增加 Chat 页面。
2. Chat submit 先走 SpiceDB `chat.run`。
3. 创建 `agent_runs`。
4. 流式接收 Hermes events。
5. 写 `cloud_sessions`、`cloud_messages`、`cloud_tool_calls`。
6. UI 展示 memory used IDs、tool activity、permission block。
7. 会话可搜索、导出、删除。

## Phase 2 出口标准

- Alice personal memory 不能被 Bob 召回。
- org A team memory 不能被 org B 召回。
- Agent 可同时使用 personal 和 team_shared。
- team_shared 默认进入 review。
- Gateway 至少一个平台可绑定并进入团队会话。
- P95 prefetch 有基线并写入追踪文档。

