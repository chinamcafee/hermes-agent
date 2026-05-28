# P2-20 隔离测试套件

日期：2026-05-22
状态：Implemented
前置：`P2-19 Runtime event bridge`

> 2026-05-24 更新：Go 服务端和 Dashboard 管理面已取消部署级 service token。本文隔离矩阵中的 API Server trusted headers 条目是 P2 阶段历史验证口径；后续 CLI / Gateway / API Server 身份透传应改用成员级 token、OIDC/JWT 或 PAT。

## 目标

本步骤把 P2 已完成的双层记忆、可信身份、Gateway session prefix、Web Chat、云会话历史和 runtime event bridge 固化为可重复执行的隔离 smoke。该套件用于在 P3/P4 阶段快速发现跨成员、跨团队、跨组织和跨会话的权限/数据隔离回归。

## 工件

| 工件 | 用途 |
| --- | --- |
| `scripts/team-cloud-isolation-smoke.sh` | P2 隔离 smoke 脚本，串联 identity、memory、Gateway、cloud history 和 runtime bridge 测试。 |
| `teamDoc/GADoc/artifacts/p2-isolation-suite-v0.json` | 隔离验收矩阵，记录每个隔离域和验证命令。 |
| `tests/team_cloud/test_isolation_suite.py` | 验证隔离脚本和矩阵覆盖必要边界。 |
| `scripts/team-cloud-foundation-smoke.sh` | 纳入 `test_isolation_suite.py`，确保套件工件持续被检查。 |
| `teamDoc/GALog/2026-05-22-p2-20-isolation-test-suite.md` | TDD 红绿记录和回归证据。 |

## 覆盖域

| Domain | 覆盖内容 |
| --- | --- |
| `personal_memory_isolation` | personal memory 只能按当前 member 召回，shared session 可关闭 personal partition。 |
| `team_memory_authz_isolation` | team_shared 记忆召回和写入路径保持 Team Cloud/AuthZ gate。 |
| `gateway_team_identity_session_prefix` | Gateway external identity resolve、未绑定提示和 org/team session key prefix。 |
| `api_server_trusted_identity_headers` | API Server trusted headers 必须在成员级 token、OIDC/JWT 或 PAT 校验通过后才接受；P2 历史实现曾使用 service token gate，已被 GTC-60~64 口径取代。 |
| `cloud_history_org_project_member_filter` | cloud sessions 按 org/project/member/q 过滤。 |
| `runtime_event_bridge_session_binding` | runtime events 绑定 cloud session/run，并写入 message/tool history。 |

## 执行方式

```bash
scripts/team-cloud-isolation-smoke.sh
```

该脚本先确认 `p2-isolation-suite-v0.json` 存在，再运行当前 P2 隔离关键路径测试。

## 非目标

- 不替代完整 foundation smoke；它是更窄的 P2 隔离回归集合。
- 不做 P3 工具风险审批和备份治理测试；P3 阶段会新增专用套件。
- 不接入外部数据库/SpiceDB 实例；当前仍使用 repo 内本地 fake/in-memory 路径保证快速回归。

## 验证

- 红灯：缺少隔离 smoke 脚本和隔离矩阵。
- 绿灯：补齐脚本、矩阵和工件测试后，隔离套件测试通过。
