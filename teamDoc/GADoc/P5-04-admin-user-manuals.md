# P5-04 管理员和用户手册

日期：2026-05-23
状态：Implemented
前置：`P4 Beta 验证`、`P5-03 安装指南`

## 目标

本步骤固定 Team Cloud GA 管理员手册和用户手册 contract。管理员手册覆盖组织、成员、权限、记忆治理、备份恢复、工具策略和审计；用户手册覆盖首次登录、团队聊天、个人记忆、团队记忆、review queue、自助备份和工具审批请求。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/admin_user_manuals.py` | `build_admin_user_manual_package()` 生成手册包 JSON contract。 |
| `scripts/team-cloud-admin-user-manuals.py` | 写出 admin/user manuals JSON artifact。 |
| `teamDoc/GADoc/artifacts/release/team-cloud-admin-user-manuals-v0.json` | P5-04 手册包 artifact。 |
| `tests/team_cloud/test_admin_user_manuals.py` | P5-04 contract 测试。 |

## 管理员手册

| Section | 操作说明 | 验证入口 |
| --- | --- | --- |
| `organization_setup` | 创建组织、冻结 slug、配置 Casdoor identity，并确认初始 SpiceDB relationship。 | `tests/team_cloud/test_admin_org_api.py` |
| `member_lifecycle` | 邀请、查看、禁用成员，确保禁用会写 relationship delete outbox intent。 | `tests/team_cloud/test_admin_org_api.py` |
| `role_permission_matrix` | 使用 Permission Explorer 校验 owner/admin/member/guest 的正反权限。 | `tests/team_cloud/test_permission_explorer_ga.py` |
| `memory_governance` | 管理 personal/team_shared memory review queue、冲突、PII 标记和 retention。 | `tests/team_cloud/test_memory_review_api.py` |
| `backup_restore_operations` | 执行个人备份策略、加密导出、MinIO 上传、restore preview 和 restore execute。 | `tests/team_cloud/test_platform_backup_restore_drill.py` |
| `tool_policy_management` | 维护工具风险 taxonomy、高危工具审批、break-glass 和 tool audit。 | `tests/team_cloud/test_team_tool_policy_hook.py` |
| `audit_review` | 按 actor、action、decision、resource 和高危工具视图过滤审计事件。 | `tests/team_cloud/test_audit_advanced.py` |

## 用户手册

| Section | 操作说明 | 验证入口 |
| --- | --- | --- |
| `first_login` | 通过 Casdoor 登录，确认 membership，并进入 Web Chat。 | `tests/team_cloud/test_web_chat_entry.py` |
| `team_chat` | 从 Web、API 或 Gateway 使用团队身份启动会话。 | `tests/team_cloud/test_cloud_session_history.py` |
| `personal_memory` | 创建、查看、归档、恢复和删除个人记忆，确认不会跨成员泄漏。 | `tests/team_cloud/test_memory_crud_api.py` |
| `team_shared_memory` | 使用团队共享记忆记录组织可见事实，并走 review/dedupe 流程。 | `tests/team_cloud/test_memory_prefetch_pipeline.py` |
| `review_queue` | 接受、拒绝或升级候选记忆和冲突项。 | `tests/team_cloud/test_memory_review_api.py` |
| `backup_self_service` | 理解个人备份周期、restore preview、组织导出和删除请求流程。 | `tests/team_cloud/test_backup_restore_drill.py` |
| `tool_approval_requests` | 发起高危工具使用请求，并根据 deny reason 调整操作。 | `tests/team_cloud/test_team_tool_policy_hook.py` |

## 核心流程

| Workflow | Owner | 步骤 | 成功标准 |
| --- | --- | --- | --- |
| `org_member_management` | Org Owner | `organization_setup`、`member_lifecycle`、`role_permission_matrix` | 禁用成员失去 relationship，新管理员通过 permission check。 |
| `memory_review` | Team Admin | `memory_governance`、`review_queue`、`team_shared_memory` | team_shared memory 仅在组织内可见，personal_memory 保持成员隔离。 |
| `backup_restore` | SRE 或 Org Owner | `backup_restore_operations`、`backup_self_service` | restore preview 先审阅后执行，保留 audit evidence。 |
| `tool_policy_change` | Security Admin | `tool_policy_management`、`tool_approval_requests`、`audit_review` | 高危工具变更需要审批并产生日志。 |

## 运行

```bash
scripts/team-cloud-admin-user-manuals.py --output teamDoc/GADoc/artifacts/release/team-cloud-admin-user-manuals-v0.json
```

## 验证

```bash
scripts/run_tests.sh tests/team_cloud/test_admin_user_manuals.py
scripts/run_tests.sh tests/team_cloud/test_admin_user_manuals.py tests/team_cloud/test_admin_org_api.py tests/team_cloud/test_memory_review_api.py tests/team_cloud/test_backup_restore_drill.py tests/team_cloud/test_team_tool_policy_hook.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/ruff check team_cloud/admin_user_manuals.py scripts/team-cloud-admin-user-manuals.py tests/team_cloud/test_admin_user_manuals.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m py_compile team_cloud/admin_user_manuals.py scripts/team-cloud-admin-user-manuals.py tests/team_cloud/test_admin_user_manuals.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m json.tool teamDoc/GADoc/artifacts/release/team-cloud-admin-user-manuals-v0.json >/dev/null
scripts/team-cloud-foundation-smoke.sh
```
