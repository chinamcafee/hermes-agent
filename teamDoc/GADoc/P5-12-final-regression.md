# P5-12 Final regression

日期：2026-05-23
状态：Implemented
前置：`P5-01..P5-11`

## 目标

本步骤固定 Team Cloud GA final regression gate，覆盖全量测试、负测、备份恢复和权限矩阵。P5-12 是进入 deployment smoke 前的质量闸门，要求所有回归门槛失败数为 0，且 final security review 中 Critical/High 未关闭发现数为 0。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/final_regression.py` | `build_final_regression_package()` 生成 final regression JSON contract。 |
| `scripts/team-cloud-final-regression.py` | 写出 final regression JSON artifact。 |
| `teamDoc/GADoc/artifacts/release/team-cloud-final-regression-v0.json` | P5-12 final regression artifact。 |
| `tests/team_cloud/test_final_regression.py` | P5-12 contract 测试。 |

## Gates

| Gate | Command | 覆盖 |
| --- | --- | --- |
| `full_foundation_smoke` | `scripts/team-cloud-foundation-smoke.sh` | P1 平台、P2 记忆、P3 治理、P4 Beta、P5 发布包 |
| `security_negative_suite` | `scripts/run_tests.sh tests/team_cloud/test_platform_security_negative.py tests/team_cloud/test_security_test_suite.py tests/team_cloud/test_final_security_review.py` | authn/authz/tool policy 负测 |
| `backup_restore_drill` | `scripts/run_tests.sh tests/team_cloud/test_backup_restore_drill.py tests/team_cloud/test_platform_backup_restore_drill.py tests/team_cloud/test_restore_preview.py tests/team_cloud/test_restore_execute.py` | 备份导出、MinIO 存储、restore preview、restore execute |
| `permission_matrix` | `scripts/run_tests.sh tests/team_cloud/test_permission_explorer_ga.py tests/team_cloud/test_team_tool_policy_hook.py tests/team_cloud/test_authz_chaos.py` | 成员/管理员边界、工具风险策略、AuthZ chaos |

## Acceptance thresholds

- `failed_tests == 0`
- `open_critical_or_high_findings == 0`
- `unreviewed_backup_restore_drills == 0`
- `permission_matrix_exceptions == 0`

## 运行

```bash
scripts/team-cloud-final-regression.py --output teamDoc/GADoc/artifacts/release/team-cloud-final-regression-v0.json
```

## 验证

```bash
scripts/run_tests.sh tests/team_cloud/test_final_regression.py
scripts/run_tests.sh tests/team_cloud/test_final_regression.py tests/team_cloud/test_platform_security_negative.py tests/team_cloud/test_security_test_suite.py tests/team_cloud/test_final_security_review.py tests/team_cloud/test_platform_backup_restore_drill.py tests/team_cloud/test_permission_explorer_ga.py tests/team_cloud/test_team_tool_policy_hook.py tests/team_cloud/test_authz_chaos.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/ruff check team_cloud/final_regression.py scripts/team-cloud-final-regression.py tests/team_cloud/test_final_regression.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m py_compile team_cloud/final_regression.py scripts/team-cloud-final-regression.py tests/team_cloud/test_final_regression.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m json.tool teamDoc/GADoc/artifacts/release/team-cloud-final-regression-v0.json >/dev/null
scripts/team-cloud-foundation-smoke.sh
```
