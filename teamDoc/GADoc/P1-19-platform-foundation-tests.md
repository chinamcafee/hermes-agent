# P1-19 平台基础测试

日期：2026-05-22
状态：Implemented
前置：`P1-13 组织/团队/成员 API`、`P1-15 MinIO client 和 manifest`、`P1-18 权限解释最小页`

## 目标

本步骤固化 P1 平台基础 smoke 测试入口，覆盖 API、auth、authz、relationship outbox、MinIO manifest 和 Web 管理壳。目标是让后续 P1-20 安全负测、P2 集成开发和本地 compose 验证有一个稳定的快速回归入口。

## 工件

| 工件 | 用途 |
| --- | --- |
| `teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json` | 机器可读 smoke 覆盖矩阵。 |
| `scripts/team-cloud-foundation-smoke.sh` | 一键运行 P1 foundation smoke 测试。 |
| `tests/team_cloud/test_platform_foundation_suite.py` | smoke matrix、脚本入口和跨模块集成回归测试。 |

## 覆盖范围

- API：组织、团队、成员、permission explain。
- Auth：Casdoor OIDC、JWT middleware、PAT/service account。
- AuthZ：SpiceDB client、AuthZ middleware、schema CI。
- Outbox：relationship outbox 和成员禁用 relationship delete intent。
- MinIO：bucket、manifest、signed URL。
- Web：登录壳、管理页、permission explain wiring。

## 运行方式

```bash
scripts/team-cloud-foundation-smoke.sh
```

脚本调用 `scripts/run_tests.sh`，遵循项目现有虚拟环境探测策略。

## 非目标

- 不启动完整 compose 栈。
- 不连接真实 Casdoor、SpiceDB、PostgreSQL 或 MinIO。
- 不替代 P1-20 安全负测。
- 不替代 P4/P5 部署 smoke 和演练。

## 后续衔接

- `P1-20`：在该 smoke 基础上增加伪造 token、禁用用户、跨 org 管理拒绝等安全负测。
- `P4/P5`：扩展为真实部署 smoke 和 final regression。
