# P5-15 Post-GA backlog 工作日志

## 背景

- 工作包：`P5-15 | Post-GA backlog | GA 后优化和运营待办 | P5-01..P5-14 | 0.5`
- 当前阶段：P5 GA 发布，P5-01 到 P5-14 已完成。

## 执行计划

1. 用 contract 测试定义 Post-GA backlog 的分组、优先级和 GA 不阻塞规则。
2. 新增 post-GA backlog builder 和生成脚本。
3. 新增 P5-15 文档和 JSON artifact。
4. 将 post-GA backlog 注册到 smoke 矩阵和 foundation smoke。
5. 完成 P5-15 后关闭 P5 和 M5 GA Sign-off。
6. 运行红灯、绿灯、关联回归、静态检查和完整 smoke。

## 实时记录

- 2026-05-23：P5-15 已在进度表中标记为 In Progress，准备按 TDD 红绿循环推进。
- 2026-05-23：新增红灯测试 `tests/team_cloud/test_post_ga_backlog.py` 并更新 `tests/team_cloud/test_ga_signoff.py`，确认失败原因为缺失 `team_cloud.post_ga_backlog` 且 GA sign-off 仍为 `ga_candidate`。
- 2026-05-23：新增 `team_cloud/post_ga_backlog.py`、`scripts/team-cloud-post-ga-backlog.py`、`teamDoc/GADoc/P5-15-post-ga-backlog.md` 和 `teamDoc/GADoc/artifacts/release/team-cloud-post-ga-backlog-v0.json`。
- 2026-05-23：将 `team_cloud/ga_signoff.py`、`teamDoc/GADoc/P5-08-ga-sign-off.md` 和 `teamDoc/GADoc/artifacts/release/team-cloud-ga-sign-off-v0.json` 从 GA candidate 更新为 GA final sign-off：`gate=ga`、`m5_final_signoff=signed`。
- 2026-05-23：将 `post_ga_backlog` 注册到 `scripts/team-cloud-foundation-smoke.sh`、`tests/team_cloud/test_platform_foundation_suite.py` 和 `teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json`。
- 2026-05-23：验证通过：
  - `scripts/run_tests.sh tests/team_cloud/test_post_ga_backlog.py tests/team_cloud/test_ga_signoff.py`：4 tests passed。
  - `scripts/run_tests.sh tests/team_cloud/test_post_ga_backlog.py tests/team_cloud/test_ga_signoff.py tests/team_cloud/test_final_regression.py tests/team_cloud/test_deployment_smoke.py tests/team_cloud/test_legal_compliance_package.py tests/team_cloud/test_platform_foundation_suite.py`：13 tests passed。
  - `venv/bin/ruff check team_cloud/post_ga_backlog.py team_cloud/ga_signoff.py scripts/team-cloud-post-ga-backlog.py scripts/team-cloud-ga-sign-off.py tests/team_cloud/test_post_ga_backlog.py tests/team_cloud/test_ga_signoff.py tests/team_cloud/test_platform_foundation_suite.py`：All checks passed。
  - `venv/bin/python -m py_compile team_cloud/post_ga_backlog.py team_cloud/ga_signoff.py scripts/team-cloud-post-ga-backlog.py scripts/team-cloud-ga-sign-off.py tests/team_cloud/test_post_ga_backlog.py tests/team_cloud/test_ga_signoff.py tests/team_cloud/test_platform_foundation_suite.py`：通过。
  - `venv/bin/python -m json.tool teamDoc/GADoc/artifacts/release/team-cloud-post-ga-backlog-v0.json >/dev/null && venv/bin/python -m json.tool teamDoc/GADoc/artifacts/release/team-cloud-ga-sign-off-v0.json >/dev/null && venv/bin/python -m json.tool teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json >/dev/null`：通过。
  - `scripts/team-cloud-foundation-smoke.sh`：101 files, 312 tests passed, 0 failed。
  - `git diff --check -- ...`：通过。
