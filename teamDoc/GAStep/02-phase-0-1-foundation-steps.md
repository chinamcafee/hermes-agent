# 02. Phase 0-1：从 0 建立 GA 平台基础

## P0 执行顺序

1. `P0-01` 冻结 GA 范围：把团队 Agent 的 GA 必须项、Beta 可缺项、明确不做项写成一页决策。
2. `P0-02` 审计 Hermes 改动边界：列出 `run_agent.py`、`agent/agent_init.py`、`gateway/run.py`、`gateway/platforms/api_server.py`、memory provider、plugin hook 的改动点。
3. `P0-03` 编写 ADR 套件：每个 ADR 必须包含背景、决策、备选、后果、回滚条件。
4. `P0-04` 冻结组件版本：Casdoor、SpiceDB、PostgreSQL、pgvector、MinIO、Go Team Cloud 服务端、客户端 SDK 均 pin 版本。
5. `P0-05` 设计本地拓扑：端口、网络、volume、初始化数据、secret 注入、健康检查。
6. `P0-06` 跑通 Casdoor OIDC：拿到 id_token，验证 issuer/audience/signature/exp。
7. `P0-07` 写 SpiceDB schema v0：覆盖 organization/team/project/session/memory/document/tool/backup。
8. `P0-08` 写 PostgreSQL schema v0：包含身份、权限 outbox、memory、backup、audit。
9. `P0-09` 写 MinIO key/manifest 规范：个人备份、组织导出、附件、文档原文。
10. `P0-10` 写 GA 验收矩阵：安全、性能、备份恢复、发布、文档。
11. `P0-11` 登记风险：MinIO AGPL、SpiceDB 一致性、pgvector 性能、Hermes core patch。
12. `P0-12` 输出阶段计划：每个 work package 的 owner、依赖、目标周次。

## P1 实施步骤

### 1. Team Cloud 骨架

1. 建立 `team_cloud_go/` Go module。
2. 建立 `team-cloud-server`、HTTP API、PostgreSQL migration、test fixtures。
3. 定义配置加载优先级：env、yaml、secret file。
4. 建立 request context：`request_id/org_id/member_id/actor_type`。
5. 加入 structured logging 和 health endpoints。

### 2. 本地 compose 栈

1. 创建 `deploy/team-cloud/compose.yaml`。
2. 加入 Casdoor service 和初始化配置。
3. 加入 SpiceDB service、pre-shared key、schema load job。
4. 加入 PostgreSQL，启用 pgvector extension。
5. 加入 MinIO，初始化 buckets。
6. 加入 Go Team API、worker、web shell。
7. 写 smoke test：登录、check permission、pgvector query、MinIO upload。

### 3. Casdoor 接入

1. 在 Casdoor 创建 Team Web 和 Team API application。
2. 实现 OIDC callback。
3. 实现 JWKS cache 和 key rotation。
4. 实现 JWT middleware。
5. 实现 user/member lazy upsert。
6. 实现 Casdoor org/group reconcile worker。
7. 实现 disabled user propagation。
8. 实现 login/logout audit。

### 4. SpiceDB 接入

1. 落地 `schema.zed`。
2. 写 permission fixture：owner/admin/member/guest/service account。
3. 实现 SpiceDB client。
4. 实现 relationship outbox 表。
5. 实现 outbox worker。
6. 实现 dead letter 和告警。
7. 实现 authorization middleware。
8. 为组织/团队/成员 API 全部加 permission gate。

### 5. 平台管理 API 和 Web

1. 实现 organization/team/project/member CRUD。
2. 实现 invite/accept/disable/remove。
3. 实现 PAT/service account。
4. 实现 audit query。
5. 实现 MinIO object manifest API。
6. Web 登录后展示 organization switcher。
7. Web 实现 members、teams、roles、permission explorer 最小页。
8. 所有页面实现 permission denied、empty、error、loading。

## Phase 0-1 出口标准

- 新开发者可以通过一条文档路径启动全栈。
- Casdoor 登录后能访问 Team API。
- Team API 所有管理端点都有 SpiceDB check。
- 成员禁用后无法访问 API。
- PostgreSQL migrations 可重复执行。
- MinIO bucket 和 manifest 写入可用。
- P1 所有安全负测通过。
