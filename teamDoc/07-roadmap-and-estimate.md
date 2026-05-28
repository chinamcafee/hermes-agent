# 07. GA 路线图与工作量估算

本路线图以 GA 产品交付为目标，不再把 PoC/MVP 作为最终口径。可以做内部里程碑，但每个阶段都必须沿用 `Casdoor + SpiceDB + PostgreSQL/pgvector + 可选 MinIO/S3-compatible` 的最终架构，避免后续推倒重来。

## 1. 总体估算

| 阶段 | 时间 | 工作量 | 目标 |
| --- | ---: | ---: | --- |
| Phase 0 架构冻结 | 2-3 周 | 8-12 人周 | 技术栈、schema、权限模型、GA 验收冻结 |
| Phase 1 平台基础 | 6-8 周 | 35-50 人周 | Casdoor、SpiceDB、PostgreSQL、可选对象存储、Team API、基础管理台 |
| Phase 2 记忆与 Hermes 集成 | 8-10 周 | 45-65 人周 | TeamMemoryProvider、团队记忆、CLI 本地个人记忆边界、pgvector、Gateway/API/Web 接入 |
| Phase 3 数据治理与权限硬化 | 6-8 周 | 35-50 人周 | 审计、备份恢复、导出删除、工具权限、权限解释 |
| Phase 4 Beta 验证 | 6-8 周 | 25-40 人周 | 私有化部署、压测、安全测试、迁移、可观测性 |
| Phase 5 GA 发布 | 4-6 周 | 17-23 人周 | 文档、Runbook、升级、发布包、最终验收 |

总计：约 `7-9 个月`，`165-240 人周`。

## 2. 推荐团队

| 角色 | 人数 | 主要职责 |
| --- | ---: | --- |
| 后端/平台工程师 | 2 | Team API、PostgreSQL schema、Casdoor、SpiceDB、可选对象存储 |
| Hermes/runtime 工程师 | 1-2 | TeamMemoryProvider、Gateway/API Server patch、tool policy hook |
| 前端/产品工程师 | 1-2 | Team Web Console、权限 UI、记忆管理、备份恢复 |
| DevOps/SRE | 1 | compose/helm、备份恢复、观测、发布包 |
| QA/安全 | 1 | 权限矩阵、安全测试、回归、压测 |
| 产品/设计 | 0.5-1 | GA 需求、信息架构、验收标准 |

最低可行 GA 团队是 5 人，理想团队是 7-8 人。

## 3. Phase 0：架构冻结

时间：2-3 周。

交付：

- ADR：Casdoor 作为 AuthN，SpiceDB 作为 AuthZ。
- ADR：PostgreSQL/pgvector 作为 canonical memory。
- ADR：MinIO/S3-compatible 作为可选对象存储，CLI 个人备份目标由用户配置。
- SpiceDB schema v0。
- PostgreSQL schema v0。
- 可选对象存储 bucket/key/manifest 规范。
- Hermes 改动边界清单。
- GA 验收标准和权限矩阵。

验收：

- 本地 compose/minikube 可启动 Casdoor、SpiceDB、PostgreSQL+pgvector，并可选启动 MinIO。
- Web 登录能拿到 Casdoor token。
- Team API 能校验 JWT。
- Team API 能写入一条 SpiceDB relationship 并 check。
- PostgreSQL 能执行一次 pgvector 查询。
- 启用对象存储时能上传和校验一个团队记忆备份对象。

## 4. Phase 1：平台基础

时间：6-8 周。

任务：

- Team API skeleton。
- Casdoor OIDC integration。
- Casdoor user/org/group 同步。
- Team Cloud org/team/project/member schema。
- SpiceDB schema、client、outbox worker。
- API token 和 service account。
- 基础 Web Console：登录、组织、团队、成员、角色、权限查看。
- Audit event 基础表和查询页。
- MinIO client、object manifest、signed URL。

验收：

- 用户可通过 Casdoor 登录并进入组织。
- Admin 可邀请/禁用成员。
- 成员关系能同步 SpiceDB。
- 管理 API 均有 permission check。
- 关键操作有 audit。

## 5. Phase 2：记忆与 Hermes 集成

时间：8-10 周。

任务：

- `memory_items`、`memory_embeddings`、`memory_events`、`memory_observations`。
- pgvector HNSW 索引和查询 API。
- TeamMemoryProvider。
- memory prefetch 分区注入。
- memory sync_turn observation queue。
- memory extraction worker。
- team_shared review queue。
- Team Runtime Adapter。
- API Server identity headers 可信注入。
- Gateway identity resolver。
- Web Chat 入口。

验收：

- Team Cloud 不召回 Alice personal memory；个人记忆只在本地 profile 生效。
- Team shared memory 只在授权 team/project 内召回。
- Agent 回答能同时使用本地 personal 和 Team Cloud team_shared。
- 团队共享记忆默认审核后发布。
- Gateway 至少一个平台完成绑定和对话。

## 6. Phase 3：数据治理与权限硬化

时间：6-8 周。

任务：

- TeamToolPolicyHook。
- 工具风险分级和审批策略。
- CLI `/cloud-backup memory|soul` 本地个人记忆和本地人格备份配置、下载、恢复。
- Team Cloud 团队记忆和团队父人格备份、下载、恢复。
- 组织导出。
- 删除请求和 hard delete worker。
- SpiceDB permission explorer。
- break-glass 双人审批。
- 审计高级过滤和导出。
- Secret/PII detector。

验收：

- 高危工具必须 SpiceDB allow + approval。
- CLI 个人备份可按计划生成并恢复，Team Cloud 团队记忆备份可按策略生成并恢复。
- 组织导出可在空环境回灌核心数据。
- 删除请求可追踪、可重试、可审计。
- break-glass 访问会通知和审计。

## 7. Phase 4：Beta 验证

时间：6-8 周。

任务：

- 企业私有化部署包。
- Docker Compose 和 Helm chart。
- Casdoor/SpiceDB/PostgreSQL/MinIO 备份恢复演练。
- 压测：并发聊天、pgvector 检索、SpiceDB check、MinIO 备份。
- 安全测试：跨租户、token spoofing、prompt injection、工具绕过。
- 升级迁移测试。
- 可观测性：metrics/logs/traces/dashboard。
- 成本和配额模型。

验收：

- 3 个试点团队连续使用 2 周无 P0/P1。
- 权限安全测试 100% 通过。
- RPO/RTO 演练达标。
- 备份恢复和升级演练可重复。

## 8. Phase 5：GA 发布

时间：4-6 周。

任务：

- 安装部署文档。
- 运维 Runbook。
- 安全白皮书。
- 数据处理说明。
- API 文档和 SDK 示例。
- 管理员手册。
- 用户手册。
- 最终发布检查清单。

验收：

- 新环境 1 小时内可完成基础部署。
- 管理员可按文档配置 Casdoor、SpiceDB、PostgreSQL，并可选配置 MinIO/S3-compatible 团队记忆备份。
- 备份恢复 Runbook 通过演练。
- 所有 GA 验收项签字。

## 9. 模块工作量

| 模块 | 人周 |
| --- | ---: |
| Casdoor 集成、同步、登录和 API token | 14-20 |
| SpiceDB schema、client、outbox、permission explorer | 18-26 |
| PostgreSQL/pgvector 记忆库和迁移 | 18-28 |
| TeamMemoryProvider 和 Hermes runtime 集成 | 16-24 |
| Gateway/API/Web chat 集成 | 12-18 |
| 对象存储备份、导出、恢复 | 14-22 |
| Team Web Console | 24-34 |
| 工具权限和审批 | 10-16 |
| 审计、观测、配额、成本 | 12-18 |
| 私有化部署、备份恢复、升级 | 14-22 |
| 安全测试、压测、QA、文档 | 23-32 |

## 10. 关键依赖

- 如果选用 MinIO，确认 AGPL-3.0 对目标商业化和私有化模式的影响；也可选其他 S3-compatible 服务。
- 确认 Casdoor 组织/应用/SCIM 使用方式和企业 IdP 集成范围。
- 确认 SpiceDB 部署拓扑、datastore 和备份策略。
- 确认默认 embedding provider、维度、模型切换策略。
- 确认是否需要国产化部署、离线部署、内网部署。
- 确认首批 Gateway 平台和企业试点场景。
