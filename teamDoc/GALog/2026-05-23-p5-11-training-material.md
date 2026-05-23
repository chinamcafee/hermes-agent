# P5-11 Training material 工作日志

## 背景

- 工作包：`P5-11 | Training material | 管理员培训、成员培训、FAQ | P5-04 | 0.5`
- 当前阶段：P5 GA 发布，P5-01 到 P5-10 已完成。

## 执行计划

1. 用 contract 测试定义管理员培训、成员培训、FAQ 和 artifact。
2. 新增 training material builder 和生成脚本。
3. 新增 P5-11 文档和 JSON artifact。
4. 运行红灯、绿灯、回归、静态检查和完整 smoke。

## 实时记录

- 2026-05-23：P5-11 已在进度表中标记为 In Progress，准备按 TDD 红绿循环推进。
- 2026-05-23：新增红灯测试 `tests/team_cloud/test_training_material.py`，确认失败原因为缺失 `team_cloud.training_material`。
- 2026-05-23：新增 `team_cloud/training_material.py`、`scripts/team-cloud-training-material.py`、`teamDoc/GADoc/P5-11-training-material.md` 和 `teamDoc/GADoc/artifacts/release/team-cloud-training-material-v0.json`。
- 2026-05-23：将 `training_material` 注册到 `scripts/team-cloud-foundation-smoke.sh`、`tests/team_cloud/test_platform_foundation_suite.py` 和 `teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json`。
- 2026-05-23：验证通过：
  - `scripts/run_tests.sh tests/team_cloud/test_training_material.py`：2 tests passed。
  - `scripts/run_tests.sh tests/team_cloud/test_training_material.py tests/team_cloud/test_admin_user_manuals.py tests/team_cloud/test_support_playbook.py tests/team_cloud/test_migration_guide.py tests/team_cloud/test_platform_foundation_suite.py`：11 tests passed。
  - `venv/bin/ruff check team_cloud/training_material.py scripts/team-cloud-training-material.py tests/team_cloud/test_training_material.py tests/team_cloud/test_platform_foundation_suite.py`：All checks passed。
  - `venv/bin/python -m py_compile team_cloud/training_material.py scripts/team-cloud-training-material.py tests/team_cloud/test_training_material.py tests/team_cloud/test_platform_foundation_suite.py`：通过。
  - `venv/bin/python -m json.tool teamDoc/GADoc/artifacts/release/team-cloud-training-material-v0.json >/dev/null && venv/bin/python -m json.tool teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json >/dev/null`：通过。
  - `scripts/team-cloud-foundation-smoke.sh`：97 files, 304 tests passed, 0 failed。
  - `git diff --check -- ...`：通过。
