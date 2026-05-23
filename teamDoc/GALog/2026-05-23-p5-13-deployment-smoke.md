# P5-13 Deployment smoke 工作日志

## 背景

- 工作包：`P5-13 | Deployment smoke | Docker Compose/Helm/Offline bundle smoke | P4-01..P4-03 | 1`
- 当前阶段：P5 GA 发布，P5-01 到 P5-12 已完成。

## 执行计划

1. 用 contract 测试定义 compose、helm、offline bundle 三类 deployment smoke gate 和 artifact。
2. 新增 deployment smoke builder 和生成脚本。
3. 新增 P5-13 文档和 JSON artifact。
4. 将 deployment smoke 注册到 smoke 矩阵和 foundation smoke。
5. 运行红灯、绿灯、关联回归、静态检查和完整 smoke。

## 实时记录

- 2026-05-23：P5-13 已在进度表中标记为 In Progress，准备按 TDD 红绿循环推进。
- 2026-05-23：新增红灯测试 `tests/team_cloud/test_deployment_smoke.py`，确认失败原因为缺失 `team_cloud.deployment_smoke`。
- 2026-05-23：新增 `team_cloud/deployment_smoke.py`、`scripts/team-cloud-deployment-smoke.py`、`teamDoc/GADoc/P5-13-deployment-smoke.md` 和 `teamDoc/GADoc/artifacts/release/team-cloud-deployment-smoke-v0.json`。
- 2026-05-23：将 `deployment_smoke` 注册到 `scripts/team-cloud-foundation-smoke.sh`、`tests/team_cloud/test_platform_foundation_suite.py` 和 `teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json`。
- 2026-05-23：验证通过：
  - `scripts/run_tests.sh tests/team_cloud/test_deployment_smoke.py`：2 tests passed。
  - `scripts/run_tests.sh tests/team_cloud/test_deployment_smoke.py tests/team_cloud/test_local_compose_stack.py tests/team_cloud/test_compose_hardening.py tests/team_cloud/test_helm_chart.py tests/team_cloud/test_offline_bundle.py tests/team_cloud/test_platform_foundation_suite.py`：21 tests passed。
  - `venv/bin/ruff check team_cloud/deployment_smoke.py scripts/team-cloud-deployment-smoke.py tests/team_cloud/test_deployment_smoke.py tests/team_cloud/test_platform_foundation_suite.py`：All checks passed。
  - `venv/bin/python -m py_compile team_cloud/deployment_smoke.py scripts/team-cloud-deployment-smoke.py tests/team_cloud/test_deployment_smoke.py tests/team_cloud/test_platform_foundation_suite.py`：通过。
  - `venv/bin/python -m json.tool teamDoc/GADoc/artifacts/release/team-cloud-deployment-smoke-v0.json >/dev/null && venv/bin/python -m json.tool teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json >/dev/null`：通过。
  - `scripts/team-cloud-foundation-smoke.sh`：99 files, 308 tests passed, 0 failed。
  - `git diff --check -- ...`：通过。
- 2026-05-23 GA 补审：deployment smoke artifact 的 Helm runtime command 已补齐真实本地验证序列：`helm upgrade --install`、二次 `helm upgrade --set config.logLevel=DEBUG`、`helm rollback ... 1`。
- 2026-05-23 GA 补审验证通过：
  - 红灯：`scripts/run_tests.sh tests/team_cloud/test_deployment_smoke.py` 曾因 `helm_runtime_command` 缺少 `config.logLevel=DEBUG` 失败。
  - 绿灯：`scripts/run_tests.sh tests/team_cloud/test_deployment_smoke.py`：2 tests passed。
  - 关联回归：`scripts/run_tests.sh tests/team_cloud/test_local_compose_stack.py tests/team_cloud/test_compose_hardening.py tests/team_cloud/test_offline_bundle.py tests/team_cloud/test_deployment_smoke.py tests/team_cloud/test_beta_exit_report.py tests/team_cloud/test_ga_release_checklist.py tests/team_cloud/test_release_manual.py tests/team_cloud/test_platform_foundation_suite.py`：30 tests passed。
  - 完整 smoke：`scripts/team-cloud-foundation-smoke.sh`：103 files, 322 tests passed, 0 failed。
  - `venv/bin/ruff check ...`：All checks passed。
  - `venv/bin/python -m py_compile ...`：通过。
  - JSON 校验：deployment smoke、beta exit、platform foundation smoke artifacts 均通过。
  - `docker compose -f deploy/team-cloud/compose.yaml config`：生成 625 行配置。
  - `helm lint deploy/team-cloud/helm/hermes-team-cloud`：1 chart linted, 0 failed。
  - `git diff --check -- . ':!uv.lock'`：通过。
