# P5-08 GA sign-off

日期：2026-05-23
状态：Implemented
前置：`P5-01 最终安全评审`

## 目标

本步骤最初固定 GA candidate sign-off 表、owner 和证据链接。P5-15 完成后，本文件同步更新为 GA final sign-off，`M5 final sign-off signed`。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/ga_signoff.py` | `build_ga_signoff_package()` 生成 GA final sign-off JSON contract。 |
| `scripts/team-cloud-ga-sign-off.py` | 写出 sign-off JSON artifact。 |
| `teamDoc/GADoc/artifacts/release/team-cloud-ga-sign-off-v0.json` | P5-08 sign-off artifact。 |
| `tests/team_cloud/test_ga_signoff.py` | P5-08 contract 测试。 |

## Sign-off 表

| Domain | Owner | Status | Evidence |
| --- | --- | --- | --- |
| Product requirements | Product | signed_for_ga | `teamDoc/GADoc/P0-10-ga-acceptance-matrix.md` |
| AuthN/AuthZ | Backend + Security | signed_for_ga | `team-cloud-final-security-review-v0.json` |
| Memory isolation | Runtime + QA | signed_for_ga | `teamDoc/GADoc/artifacts/p2-isolation-suite-v0.json` |
| Backup/restore | SRE | signed_for_ga | `team-cloud-backup-restore-drill-v0.json` |
| Web Console | Frontend | signed_for_ga | `teamDoc/GADoc/P3-22-admin-ux-final.md` |
| Documentation | Product + Engineering | signed_for_ga | `teamDoc/GADoc/P5-04-admin-user-manuals.md` |
| Security review | Security | signed_for_ga | `teamDoc/GADoc/P5-01-final-security-review.md` |
| Pilot acceptance | Customer/Internal | signed_for_ga | `team-cloud-beta-exit-report-v0.json` |
| Release operations | Release | signed_for_ga | `teamDoc/GADoc/P5-06-runbook-summary.md` |

## Blocking issues

| Level | Open |
| --- | ---: |
| P0 | 0 |
| P1 | 0 |

## Evidence links

- `final_security_review`：`teamDoc/GADoc/artifacts/security/team-cloud-final-security-review-v0.json`
- `beta_exit_report`：`teamDoc/GADoc/artifacts/pilot/team-cloud-beta-exit-report-v0.json`
- `release_notes`：`teamDoc/GADoc/artifacts/release/team-cloud-ga-release-notes-v0.json`
- `runbook_summary`：`teamDoc/GADoc/artifacts/release/team-cloud-runbook-summary-v0.json`
- `final_regression`：`teamDoc/GADoc/artifacts/release/team-cloud-final-regression-v0.json`
- `deployment_smoke`：`teamDoc/GADoc/artifacts/release/team-cloud-deployment-smoke-v0.json`
- `legal_compliance`：`teamDoc/GADoc/artifacts/release/team-cloud-legal-compliance-v0.json`
- `post_ga_backlog`：`teamDoc/GADoc/artifacts/release/team-cloud-post-ga-backlog-v0.json`

## 运行

```bash
scripts/team-cloud-ga-sign-off.py --output teamDoc/GADoc/artifacts/release/team-cloud-ga-sign-off-v0.json
```

## 验证

```bash
scripts/run_tests.sh tests/team_cloud/test_ga_signoff.py
scripts/run_tests.sh tests/team_cloud/test_ga_signoff.py tests/team_cloud/test_final_security_review.py tests/team_cloud/test_beta_exit_report.py tests/team_cloud/test_release_notes.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/ruff check team_cloud/ga_signoff.py scripts/team-cloud-ga-sign-off.py tests/team_cloud/test_ga_signoff.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m py_compile team_cloud/ga_signoff.py scripts/team-cloud-ga-sign-off.py tests/team_cloud/test_ga_signoff.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m json.tool teamDoc/GADoc/artifacts/release/team-cloud-ga-sign-off-v0.json >/dev/null
scripts/team-cloud-foundation-smoke.sh
```
