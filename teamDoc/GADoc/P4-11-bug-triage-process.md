# P4-11 Bug triage process

日期：2026-05-23
状态：Implemented
前置：`P4-10 Pilot onboarding`

## 目标

本步骤固定 Beta bug triage contract，包含 `severity_levels`、`release_blocker_rules` 和升级路径。P0/P1 问题会阻塞 Beta exit 和 GA sign-off。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/triage.py` | `build_bug_triage_process()` 生成分级和 SLA。 |
| `scripts/team-cloud-bug-triage.py` | 写出 bug triage JSON artifact。 |
| `teamDoc/GADoc/artifacts/pilot/team-cloud-bug-triage-v0.json` | P4-11 triage artifact。 |
| `tests/team_cloud/test_bug_triage_process.py` | P4-11 contract 测试。 |

## 运行

```bash
scripts/team-cloud-bug-triage.py --output teamDoc/GADoc/artifacts/pilot/team-cloud-bug-triage-v0.json
```

## 验证

```bash
scripts/run_tests.sh tests/team_cloud/test_bug_triage_process.py
scripts/run_tests.sh tests/team_cloud/test_bug_triage_process.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/ruff check team_cloud/triage.py scripts/team-cloud-bug-triage.py tests/team_cloud/test_bug_triage_process.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m py_compile team_cloud/triage.py scripts/team-cloud-bug-triage.py tests/team_cloud/test_bug_triage_process.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m json.tool teamDoc/GADoc/artifacts/pilot/team-cloud-bug-triage-v0.json >/dev/null
scripts/team-cloud-foundation-smoke.sh
```
