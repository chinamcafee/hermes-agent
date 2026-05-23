# P1-21 观测基线工作日志

## 目标

- 按 `GAStep` 顺序推进 P1-21。
- 增加 metrics、structured request events 和健康检查可观测基线。
- 保持本地测试不依赖外部 Prometheus 或日志后端。

## 执行记录

- 2026-05-22：启动 P1-21，读取 Team API health/readiness、request context 和 P1-21 工作包要求。
- 2026-05-22：按 TDD 新增 `tests/team_cloud/test_observability_baseline.py`，覆盖 `/metrics` 请求计数、结构化请求事件和 readyz checks。
- 2026-05-22：红灯确认后新增 `team_cloud/observability.py`，在 `team_cloud/api.py` 接入 observability middleware 和 `/metrics`。
- 2026-05-22：更新 `platform-foundation-smoke-v0.json` 和 `scripts/team-cloud-foundation-smoke.sh`，纳入 observability 测试。
- 2026-05-22：新增 `teamDoc/GADoc/P1-21-observability-baseline.md`。

## 验证记录

- 红灯：`scripts/run_tests.sh tests/team_cloud/test_observability_baseline.py`
  - 结果：`1 test failed, 1 passed`。
  - 失败点：`/metrics` 返回 404，尚未接入 metrics 和结构化请求事件。
- 绿灯：`scripts/run_tests.sh tests/team_cloud/test_observability_baseline.py`
  - 结果：`2 tests passed, 0 failed`。
- Smoke 回归：`scripts/team-cloud-foundation-smoke.sh`
  - 结果：`96 tests passed, 0 failed`。
- Ruff 回归：`venv/bin/ruff check team_cloud tests/team_cloud`
  - 结果：`All checks passed!`。
- 语法检查：`venv/bin/python -m compileall -q team_cloud`
  - 结果：退出码 0。
