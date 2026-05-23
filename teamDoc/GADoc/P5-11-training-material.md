# P5-11 Training material

日期：2026-05-23
状态：Implemented
前置：`P5-04 管理员和用户手册`

## 目标

本步骤固定 Team Cloud GA training material contract，覆盖管理员培训、成员培训、FAQ 和 hands-on labs。材料面向开箱即用团队版交付，默认与 P5 安装指南、管理员/用户手册、support playbook、migration guide 对齐。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/training_material.py` | `build_training_material_package()` 生成 training material JSON contract。 |
| `scripts/team-cloud-training-material.py` | 写出 training material JSON artifact。 |
| `teamDoc/GADoc/artifacts/release/team-cloud-training-material-v0.json` | P5-11 training material artifact。 |
| `tests/team_cloud/test_training_material.py` | P5-11 contract 测试。 |

## 管理员培训

管理员培训覆盖：

- `organization_setup`
- `member_lifecycle`
- `tool_policy_management`
- `backup_restore_operations`

管理员培训前置阅读 `P5-03 install guide` 和 `P5-04 admin manual`，重点确认组织创建、成员邀请/禁用、工具策略和备份恢复演练。

## 成员培训

成员培训覆盖：

- `first_login`
- `team_chat`
- `personal_memory`
- `team_shared_memory`

成员培训前置阅读 `P5-04 user manual`，重点确认首次登录、团队聊天入口、个人记忆与团队共享记忆的边界。

## FAQ

FAQ 覆盖：

- `identity_map`
- `permission_denied`
- `backup_restore`
- `offline_bundle`

FAQ 来源与 P5-03、P5-04、P5-09、P5-10 对齐，避免培训材料和 GA 操作手册分叉。

## Hands-on labs

1. `create_org_and_invite_member`
2. `memory_review_flow`
3. `run_foundation_smoke`

## 运行

```bash
scripts/team-cloud-training-material.py --output teamDoc/GADoc/artifacts/release/team-cloud-training-material-v0.json
```

## 验证

```bash
scripts/run_tests.sh tests/team_cloud/test_training_material.py
scripts/run_tests.sh tests/team_cloud/test_training_material.py tests/team_cloud/test_admin_user_manuals.py tests/team_cloud/test_support_playbook.py tests/team_cloud/test_migration_guide.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/ruff check team_cloud/training_material.py scripts/team-cloud-training-material.py tests/team_cloud/test_training_material.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m py_compile team_cloud/training_material.py scripts/team-cloud-training-material.py tests/team_cloud/test_training_material.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m json.tool teamDoc/GADoc/artifacts/release/team-cloud-training-material-v0.json >/dev/null
scripts/team-cloud-foundation-smoke.sh
```
