# P1-07 Casdoor 同步 worker

日期：2026-05-22
状态：Implemented
前置：`P1-06 JWT 中间件`

## 目标

本步骤把 Casdoor 目录生命周期转换为 Team Cloud 的身份、成员、团队、审计和授权关系 outbox 意图。当前实现先落地可测试的服务层和 worker 承载点，真实 PostgreSQL repository、Casdoor webhook、SCIM 和 relationship outbox worker 在后续 P1 工作包继续接入。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/sync/casdoor.py` | Casdoor payload 规范化、lazy upsert、reconcile、禁用传播。 |
| `team_cloud/sync/__init__.py` | 同步 primitives 包导出。 |
| `team_cloud/worker.py` | `TeamCloudWorker.run_casdoor_reconcile()` 承载 Casdoor reconcile。 |
| `tests/team_cloud/test_casdoor_sync_worker.py` | lazy upsert、reconcile、disabled propagation、worker 承载测试。 |

## 行为

- 登录 lazy upsert：
  - 从 OIDC claims 读取 `sub/email/name/organization/groups/roles`。
  - upsert `team_cloud_users`、`organizations`、`members`、`external_identities`。
  - 将 Casdoor groups 规范化为 Team Cloud team slug，并写入团队成员关系意图。
  - 记录 `casdoor.lazy_upsert` audit。
- 定时 reconcile：
  - 通过注入的 Casdoor directory client 读取 organizations、groups、users。
  - organizations 映射到 Team Cloud organizations。
  - groups 映射到 Team Cloud teams。
  - users 映射到 user/member/external identity/team membership。
  - 记录 `casdoor.reconcile` audit。
- 禁用传播：
  - Casdoor `isForbidden/isDeleted/disabled/status` 映射为 suspended member。
  - 记录 session revoke intent。
  - 记录 PAT revoke pending intent，真实撤销在 P1-08 接入。
  - 写入 SpiceDB relationship delete outbox 意图。
  - 记录 `casdoor.user_disabled` audit。
- 敏感字段处理：
  - `token/secret/password/credential` key 不进入 `SyncResult` 或 external identity metadata。

## 非目标

- 不直接连接 PostgreSQL。
- 不引入 Casdoor SDK。
- 不实现 webhook、SCIM endpoint。
- 不消费 `spicedb_outbox`。
- 不真实撤销 PAT，P1-08 落地 token hash、scope、过期、撤销和审计。

## 后续衔接

- P1-08：将 disabled propagation 里的 PAT pending intent 接入真实 token revoke。
- P1-09 到 P1-11：将 relationship touch/delete intent 接入 SpiceDB client 和 outbox worker。
- P1-13：将成员和团队 API 接入同一 repository 合约。
