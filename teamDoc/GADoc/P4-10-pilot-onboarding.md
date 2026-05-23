# P4-10 Pilot onboarding

日期：2026-05-23
状态：Implemented
前置：`P4-01 Compose hardening`

## 目标

本步骤固定 Beta 试点 onboarding contract：选择 3 个团队，导入 Casdoor group 成员和初始项目，配置 Gateway 平台，连续运行 14 天，并按周汇总 usage、latency、errors、security_events 和 backup_jobs。

核心 artifact 字段为 `pilot_teams`、`schedule`、`feedback` 和 `weekly_review`。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/pilot.py` | `build_pilot_onboarding_plan()` 生成试点 onboarding 计划。 |
| `scripts/team-cloud-pilot-onboarding.py` | 写出 pilot onboarding JSON artifact。 |
| `teamDoc/GADoc/artifacts/pilot/team-cloud-pilot-onboarding-v0.json` | P4-10 onboarding artifact。 |
| `tests/team_cloud/test_pilot_onboarding.py` | P4-10 contract 测试。 |

## 运行

```bash
scripts/team-cloud-pilot-onboarding.py --output teamDoc/GADoc/artifacts/pilot/team-cloud-pilot-onboarding-v0.json
```

## 验证

```bash
scripts/run_tests.sh tests/team_cloud/test_pilot_onboarding.py
scripts/run_tests.sh tests/team_cloud/test_pilot_onboarding.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/ruff check team_cloud/pilot.py scripts/team-cloud-pilot-onboarding.py tests/team_cloud/test_pilot_onboarding.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m py_compile team_cloud/pilot.py scripts/team-cloud-pilot-onboarding.py tests/team_cloud/test_pilot_onboarding.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m json.tool teamDoc/GADoc/artifacts/pilot/team-cloud-pilot-onboarding-v0.json >/dev/null
scripts/team-cloud-foundation-smoke.sh
```
