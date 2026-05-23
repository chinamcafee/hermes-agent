# P4-12 Cost/quotas tuning

日期：2026-05-23
状态：Implemented
前置：`P3-17 Usage/quotas`

## 目标

本步骤固定 Beta 默认成本和额度策略，包含 `default_quotas`、`alert_thresholds`、`dashboard_signals` 和 `limit_alerts`。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/usage.py` | 新增 `build_cost_quota_tuning()`。 |
| `scripts/team-cloud-cost-quotas.py` | 写出 cost/quota tuning JSON artifact。 |
| `teamDoc/GADoc/artifacts/usage/team-cloud-cost-quotas-v0.json` | P4-12 quota tuning artifact。 |
| `tests/team_cloud/test_cost_quota_tuning.py` | P4-12 contract 测试。 |

## 运行

```bash
scripts/team-cloud-cost-quotas.py --output teamDoc/GADoc/artifacts/usage/team-cloud-cost-quotas-v0.json
```

## 验证

```bash
scripts/run_tests.sh tests/team_cloud/test_cost_quota_tuning.py
scripts/run_tests.sh tests/team_cloud/test_cost_quota_tuning.py tests/team_cloud/test_usage_quotas.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/ruff check team_cloud/usage.py scripts/team-cloud-cost-quotas.py tests/team_cloud/test_cost_quota_tuning.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m py_compile team_cloud/usage.py scripts/team-cloud-cost-quotas.py tests/team_cloud/test_cost_quota_tuning.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m json.tool teamDoc/GADoc/artifacts/usage/team-cloud-cost-quotas-v0.json >/dev/null
scripts/team-cloud-foundation-smoke.sh
```
