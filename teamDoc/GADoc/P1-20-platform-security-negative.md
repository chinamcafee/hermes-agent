# P1-20 平台安全负测

日期：2026-05-22
状态：Implemented
前置：`P1-19 平台基础测试`

## 目标

本步骤为 P1 平台基础增加安全负测，覆盖伪造 token、禁用用户和跨组织管理拒绝。实现重点是把 P1-12 的 AuthZ middleware 以可选方式接入组织/团队/成员管理 API，使管理端点在启用时按组织资源 fail-closed。

## 工件

| 工件 | 用途 |
| --- | --- |
| `tests/team_cloud/test_platform_security_negative.py` | 平台安全负测。 |
| `team_cloud/api.py` | 新增 `enable_authz_middleware`、`authz_subject_resolver`、`authz_outbox_pending` 注入，并安装管理 API 路由权限规则。 |
| `teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json` | smoke matrix 增加 security domain。 |
| `scripts/team-cloud-foundation-smoke.sh` | P1 smoke 增加 security negative 测试。 |

## 覆盖范围

- 伪造 bearer token：
  - OIDC verification error 返回 `401 invalid_token`。
  - 响应体不泄漏原始 token。
- 禁用用户：
  - `member_status_resolver` 返回 `suspended` 时拒绝访问受保护 API。
  - 返回 `403 member_not_active`。
- 跨组织管理：
  - 启用 `enable_authz_middleware` 后，组织作用域管理路由进入 SpiceDB check。
  - 针对非授权组织的 member invite 返回 `403 permission_denied`。
  - 被拒绝的成员不会写入 service repository。

## AuthZ 路由规则

- `GET /api/organizations/{org_id}/members` -> organization `manage_members`
- `POST /api/organizations/{org_id}/members/invite` -> organization `manage_members`
- `PATCH /api/organizations/{org_id}/members/{member_id}/disable` -> organization `manage_members`

## 非目标

- 不强制所有 `create_app()` 调用默认启用 AuthZ middleware。
- 不实现跨组织数据库级 row policy。
- 不覆盖 P2/P3 记忆隔离、工具策略和备份恢复安全负测。

## 后续衔接

- `P2-20`：扩展为 Alice/Bob、org A/B、team/project 的隔离测试套件。
- `P3-02/P3-19`：工具策略 hook 和 AuthZ chaos tests 复用本阶段的 fail-closed 语义。
