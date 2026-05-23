# P5-09 Support playbook

日期：2026-05-23
状态：Implemented
前置：`P5-06 Runbook 汇总`

## 目标

本步骤固定 Team Cloud GA 支持手册 contract，覆盖 `first_response_minutes`、`diagnostic_commands`、`log_collection`、escalation paths 和 `upgrade_path`。该手册面向 on-call、支持工程师和客户成功团队。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/support_playbook.py` | `build_support_playbook_package()` 生成 support playbook JSON contract。 |
| `scripts/team-cloud-support-playbook.py` | 写出 support playbook JSON artifact。 |
| `teamDoc/GADoc/artifacts/release/team-cloud-support-playbook-v0.json` | P5-09 support playbook artifact。 |
| `tests/team_cloud/test_support_playbook.py` | P5-09 contract 测试。 |

## 支持等级

| Severity | first_response_minutes | target_update_minutes |
| --- | ---: | ---: |
| P0 | 15 | 30 |
| P1 | 60 | 120 |
| P2 | 240 | 480 |
| P3 | 1440 | 2880 |

## diagnostic_commands

| ID | Command | Purpose |
| --- | --- | --- |
| `foundation_smoke` | `scripts/team-cloud-foundation-smoke.sh` | 确认 GA contract 仍通过。 |
| `collect_hermes_logs` | `hermes logs --level WARNING --session <session-id>` | 采集 agent、errors 和 gateway 日志片段。 |
| `runbook_summary` | `scripts/team-cloud-runbook-summary.py` | 刷新 Runbook artifact 并选择事件 Runbook。 |
| `audit_export` | `GET /api/audit/export?org_id=<org-id>` | 导出支持工单审计证据。 |

## log_collection

| ID | Source |
| --- | --- |
| `agent_log` | `~/.hermes/logs/agent.log` |
| `errors_log` | `~/.hermes/logs/errors.log` |
| `gateway_log` | `~/.hermes/logs/gateway.log` |
| `team_api_logs` | Team API container or pod logs |
| `audit_export` | `/api/audit/export` |

## escalation_paths

| ID | Trigger |
| --- | --- |
| `security` | P0/P1 security、cross-tenant 或 tool abuse。 |
| `sre` | availability、backup、restore、MinIO、PostgreSQL 或 SpiceDB。 |
| `release` | upgrade、rollback、migration 或 release artifact。 |

## upgrade_path

`P5-06 runbook_summary -> P4-09 upgrade_rollback`

## handoff_artifacts

- `support_case_template`
- `customer_export_bundle`
- `audit_jsonl_export`

## 运行

```bash
scripts/team-cloud-support-playbook.py --output teamDoc/GADoc/artifacts/release/team-cloud-support-playbook-v0.json
```

## 验证

```bash
scripts/run_tests.sh tests/team_cloud/test_support_playbook.py
scripts/run_tests.sh tests/team_cloud/test_support_playbook.py tests/team_cloud/test_runbook_summary.py tests/team_cloud/test_logs_traces.py tests/team_cloud/test_audit_advanced.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/ruff check team_cloud/support_playbook.py scripts/team-cloud-support-playbook.py tests/team_cloud/test_support_playbook.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m py_compile team_cloud/support_playbook.py scripts/team-cloud-support-playbook.py tests/team_cloud/test_support_playbook.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m json.tool teamDoc/GADoc/artifacts/release/team-cloud-support-playbook-v0.json >/dev/null
scripts/team-cloud-foundation-smoke.sh
```
