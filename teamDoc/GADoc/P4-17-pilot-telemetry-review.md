# P4-17 Pilot telemetry review

日期：2026-05-23
状态：Implemented
前置：`P4-10 Pilot onboarding`

## 目标

本步骤固定 Beta 试点 telemetry review contract：3 个 pilot team 连续运行 14 天，每周汇总 usage、latency、errors、security_events、backup_jobs 和 cost_quotas。

P4-17 的输出会作为 P4-18 Beta exit report 的输入；`release_gates` 中 P0/P1、cross-org access、personal memory leakage、authz fail-open 和 backup restore failure 均必须为 0。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/telemetry_review.py` | `build_pilot_telemetry_review()` 生成 telemetry review contract。 |
| `scripts/team-cloud-pilot-telemetry-review.py` | 写出 pilot telemetry review JSON artifact。 |
| `teamDoc/GADoc/artifacts/pilot/team-cloud-pilot-telemetry-review-v0.json` | P4-17 telemetry review artifact。 |
| `tests/team_cloud/test_pilot_telemetry_review.py` | P4-17 contract 测试。 |

## 周报字段

| 字段 | 用途 |
| --- | --- |
| `usage` | run、token、tool call、backup size 和 quota 状态。 |
| `latency` | Team API、memory prefetch、SpiceDB check、worker lag。 |
| `errors` | API 5xx、worker retry、dead letter、gateway failure。 |
| `security_events` | deny、break-glass、高危工具、跨租户尝试。 |
| `backup_jobs` | personal backup、restore drill 和 MinIO operation status。 |
| `cost_quotas` | P4-12 quota warning/critical 阈值。 |

## 输出

- `weekly_report`：day-7 和 day-14 的 pilot telemetry summary。
- `security_exception_log`：安全例外、deny spike 和人工处置记录。
- `performance_delta`：P4-16 调优前后的关键延迟变化。
- `beta_exit_inputs`：P4-18 Beta exit report 的输入集合。

## 运行

```bash
scripts/team-cloud-pilot-telemetry-review.py --output teamDoc/GADoc/artifacts/pilot/team-cloud-pilot-telemetry-review-v0.json
```

## 验证

```bash
scripts/run_tests.sh tests/team_cloud/test_pilot_telemetry_review.py
scripts/run_tests.sh tests/team_cloud/test_pilot_telemetry_review.py tests/team_cloud/test_pilot_onboarding.py tests/team_cloud/test_cost_quota_tuning.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/ruff check team_cloud/telemetry_review.py scripts/team-cloud-pilot-telemetry-review.py tests/team_cloud/test_pilot_telemetry_review.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m py_compile team_cloud/telemetry_review.py scripts/team-cloud-pilot-telemetry-review.py tests/team_cloud/test_pilot_telemetry_review.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m json.tool teamDoc/GADoc/artifacts/pilot/team-cloud-pilot-telemetry-review-v0.json >/dev/null
scripts/team-cloud-foundation-smoke.sh
```
