# P3-22 Admin UX 收尾

日期：2026-05-22
状态：Implemented
前置：`P1-17 Web 成员/团队/角色页`、`P3-16 Audit 高级能力`、`P3-17 Usage/quotas`、`P3-21 通知系统`

## 目标

本步骤完成 Team Cloud 管理台 GA 前的 UX 收口，重点补齐 empty state、permission/error state 和成员批量操作确认。实现范围限定在 repo shipped web shell，不重写主 chat/TUI，也不引入前端构建链。

## 工件

| 工件 | 用途 |
| --- | --- |
| `deploy/team-cloud/web-shell/index.html` | 管理台 empty/permission state、成员批量选择和批量禁用确认对话框。 |
| `tests/team_cloud/test_admin_ux_final.py` | 静态 contract 测试，固定 GA UX 元素、helper wiring 和 smoke 注册。 |
| `teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json` | 新增 `admin_ux_final` smoke domain。 |
| `scripts/team-cloud-foundation-smoke.sh` | 将 P3-22 测试纳入 foundation smoke。 |

## UX Contract

- Teams、Members、Audit、Usage、Chat 均有独立 empty state 容器，空数据时由 `setEmptyState()` 控制显示。
- Teams、Members、Audit、Usage 均有 permission state 容器，401/403 和 `authorization_unavailable` 路径通过 `showPermissionState()` 显示可操作错误。
- Members 列表提供 `.member-select` 选择框，暂停成员不可选；选择计数由 `selectedMemberIds` 和 `updateMemberBulkControls()` 管理。
- 批量禁用必须先打开 `members-bulk-confirm` 对话框，由 `bulkDisableMembers()` 执行，不使用原生 `window.confirm`。

## 错误处理

- `apiRequest()` 在非 2xx 时保留 HTTP status 和 JSON payload，供 permission state 判定。
- `apiText()` 在导出失败时保留 HTTP status，并将错误传递给 Audit permission state。
- 成功刷新会清理对应 permission state；切换到无组织状态或退出登录会清理全部管理台 permission state。

## 非目标

- 不新增真实通知 inbox。
- 不新增 React/Vue 等构建型前端。
- 不改变成员禁用 API contract；批量禁用仍复用单成员 disable endpoint。

## 验证

```bash
scripts/run_tests.sh tests/team_cloud/test_admin_ux_final.py
scripts/run_tests.sh tests/team_cloud/test_admin_ux_final.py tests/team_cloud/test_web_admin_pages.py tests/team_cloud/test_web_login_shell.py tests/team_cloud/test_audit_advanced.py tests/team_cloud/test_usage_quotas.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/ruff check tests/team_cloud/test_admin_ux_final.py tests/team_cloud/test_web_admin_pages.py tests/team_cloud/test_web_login_shell.py tests/team_cloud/test_audit_advanced.py tests/team_cloud/test_usage_quotas.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m py_compile tests/team_cloud/test_admin_ux_final.py tests/team_cloud/test_web_admin_pages.py tests/team_cloud/test_web_login_shell.py tests/team_cloud/test_audit_advanced.py tests/team_cloud/test_usage_quotas.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m json.tool teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json >/dev/null
scripts/team-cloud-foundation-smoke.sh
```
