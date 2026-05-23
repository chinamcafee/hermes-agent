# P4-07 Load test scripts

日期：2026-05-23
状态：Implemented
前置：`P2/P3 记忆、权限和治理能力`

## 目标

本步骤固定 Team Cloud Beta 压测计划 contract。P4-07 不在单测中执行真实长时间压测，而是把场景、阈值、遥测和执行入口版本化，供试点环境用同一份 plan 接入 k6、Locust 或内部 runner。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/load_testing.py` | `build_load_test_plan()` 生成标准压测计划。 |
| `scripts/team-cloud-load-test-plan.py` | 写出 P4 load test plan JSON artifact。 |
| `teamDoc/GADoc/artifacts/load/team-cloud-load-test-plan-v0.json` | 压测计划 artifact。 |
| `tests/team_cloud/test_load_test_scripts.py` | P4-07 contract 测试。 |

## 场景

| Scenario | 目标 |
| --- | --- |
| `concurrent_chat_runs` | 并发 Web Chat runs。 |
| `memory_prefetch` | 并发 personal/team memory prefetch。 |
| `spicedb_batch_check` | 批量 permission checks。 |
| `embedding_import` | 大量 memory embedding import/backfill。 |
| `personal_backup` | 定时 personal backup。 |
| `org_export` | 组织导出。 |
| `gateway_group_session` | Gateway group session 身份解析和提交。 |

## 运行

```bash
scripts/team-cloud-load-test-plan.py --output teamDoc/GADoc/artifacts/load/team-cloud-load-test-plan-v0.json
```

## 验证

```bash
scripts/run_tests.sh tests/team_cloud/test_load_test_scripts.py
scripts/run_tests.sh tests/team_cloud/test_load_test_scripts.py tests/team_cloud/test_memory_performance_baseline.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/ruff check team_cloud/load_testing.py scripts/team-cloud-load-test-plan.py tests/team_cloud/test_load_test_scripts.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m py_compile team_cloud/load_testing.py scripts/team-cloud-load-test-plan.py tests/team_cloud/test_load_test_scripts.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m json.tool teamDoc/GADoc/artifacts/load/team-cloud-load-test-plan-v0.json >/dev/null
scripts/team-cloud-foundation-smoke.sh
```
