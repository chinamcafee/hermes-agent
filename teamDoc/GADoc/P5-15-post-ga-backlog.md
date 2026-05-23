# P5-15 Post-GA backlog

日期：2026-05-23
状态：Implemented
前置：`P5-01..P5-14`

## 目标

本步骤固定 Team Cloud Post-GA backlog，确认所有后续优化均为 non-blocking，不阻塞 M5 GA Sign-off。P5-15 完成后，P5 GA 发布阶段可关闭，`M5 GA Sign-off` 状态更新为 signed。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/post_ga_backlog.py` | `build_post_ga_backlog_package()` 生成 Post-GA backlog JSON contract。 |
| `scripts/team-cloud-post-ga-backlog.py` | 写出 Post-GA backlog JSON artifact。 |
| `teamDoc/GADoc/artifacts/release/team-cloud-post-ga-backlog-v0.json` | P5-15 Post-GA backlog artifact。 |
| `tests/team_cloud/test_post_ga_backlog.py` | P5-15 contract 测试。 |

## Backlog items

| ID | Category | Priority | Owner | GA blocker |
| --- | --- | --- | --- | --- |
| `helm_runtime_lint_ci` | release_engineering | P1 | SRE | false |
| `advanced_admin_analytics` | product | P2 | Product + Frontend | false |
| `memory_quality_iteration` | memory_runtime | P1 | Runtime | false |
| `external_audit_packet` | compliance | P2 | Security + Legal | false |

## Acceptance thresholds

- `ga_blocking_items == 0`
- `items_without_owner == 0`
- `items_without_priority == 0`

## M5 GA Sign-off

M5 GA Sign-off 状态：`signed`。

关闭依据：

- `P5-12-final-regression`
- `P5-13-deployment-smoke`
- `P5-14-legal-compliance-package`
- `P5-15-post-ga-backlog`

## 运行

```bash
scripts/team-cloud-post-ga-backlog.py --output teamDoc/GADoc/artifacts/release/team-cloud-post-ga-backlog-v0.json
```

## 验证

```bash
scripts/run_tests.sh tests/team_cloud/test_post_ga_backlog.py tests/team_cloud/test_ga_signoff.py
scripts/run_tests.sh tests/team_cloud/test_post_ga_backlog.py tests/team_cloud/test_ga_signoff.py tests/team_cloud/test_final_regression.py tests/team_cloud/test_deployment_smoke.py tests/team_cloud/test_legal_compliance_package.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/ruff check team_cloud/post_ga_backlog.py team_cloud/ga_signoff.py scripts/team-cloud-post-ga-backlog.py scripts/team-cloud-ga-sign-off.py tests/team_cloud/test_post_ga_backlog.py tests/team_cloud/test_ga_signoff.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m py_compile team_cloud/post_ga_backlog.py team_cloud/ga_signoff.py scripts/team-cloud-post-ga-backlog.py scripts/team-cloud-ga-sign-off.py tests/team_cloud/test_post_ga_backlog.py tests/team_cloud/test_ga_signoff.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m json.tool teamDoc/GADoc/artifacts/release/team-cloud-post-ga-backlog-v0.json >/dev/null
venv/bin/python -m json.tool teamDoc/GADoc/artifacts/release/team-cloud-ga-sign-off-v0.json >/dev/null
scripts/team-cloud-foundation-smoke.sh
```
