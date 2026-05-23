# P3-15 Permission Explorer GA 工作日志

日期：2026-05-22
状态：In Progress

## 目标

- 按 `GAStep` 顺序推进 P3-15。
- 在 P1-18 最小 permission explain 基础上增加 GA 所需关系路径、近期变更和 deny reason。
- 复用现有 AuthZ check contract 和 relationship outbox，不引入新的授权真相来源。
- Web Permission tab 展示决策、关系路径、近期关系变更和 deny reason。

## 执行记录

- 2026-05-22：P3-14 完成并通过 foundation smoke 后启动 P3-15。
- 2026-05-22：读取 P1-18 文档、`team_cloud/authz/explain.py`、`team_cloud/authz/outbox.py`、`team_cloud/api.py` 和 Web shell，确认本步骤在既有 `/api/authz/explain` 上增量扩展。

## TDD 记录

- 红灯：`scripts/run_tests.sh tests/team_cloud/test_permission_explorer_ga.py`
  失败符合预期，3 个测试全部失败；失败原因为
  `create_app()` 不支持 `relationship_outbox_repository` 注入，
  explain 响应缺少 GA 字段，Web Permission 面板缺少关系路径、
  近期变更和 deny reason 渲染区。
- 绿灯：扩展 `team_cloud/authz/explain.py`、`team_cloud/api.py`
  和 Web Permission 面板后重跑
  `scripts/run_tests.sh tests/team_cloud/test_permission_explorer_ga.py
  tests/team_cloud/test_permission_explorer_minimal.py`，2 个测试文件、
  6 个测试通过、0 失败。

## 回归验证

- `scripts/run_tests.sh tests/team_cloud/test_permission_explorer_ga.py
  tests/team_cloud/test_permission_explorer_minimal.py
  tests/team_cloud/test_platform_foundation_suite.py`：3 个测试文件、9 个测试通过、0 失败。
- `venv/bin/ruff check team_cloud/authz/explain.py team_cloud/api.py
  tests/team_cloud/test_permission_explorer_ga.py
  tests/team_cloud/test_permission_explorer_minimal.py
  tests/team_cloud/test_platform_foundation_suite.py`：通过。
- `venv/bin/python -m py_compile team_cloud/authz/explain.py
  team_cloud/api.py tests/team_cloud/test_permission_explorer_ga.py
  tests/team_cloud/test_permission_explorer_minimal.py
  tests/team_cloud/test_platform_foundation_suite.py`：通过。
- `venv/bin/python -m json.tool
  teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json`：通过。
- `scripts/team-cloud-foundation-smoke.sh`：61 个测试文件、214 个测试通过、0 失败。

## 完成记录

- 2026-05-22：P3-15 Permission Explorer GA 已完成，foundation smoke 纳入
  `permission_explorer_ga` domain；P3-16 Audit 高级能力承接审计过滤和导出。
