# Diff Details

Date : 2026-05-22 19:40:55

Directory /Users/changzechuan/AIProjects/AgentProjects/HermesProjects/hermes-agent

Total : 36 files,  1587 codes, -17 comments, 388 blanks, all 1958 lines

[Summary](results.md) / [Details](details.md) / [Diff Summary](diff.md) / Diff Details

## Files
| filename | language | code | comment | blank | total |
| :--- | :--- | ---: | ---: | ---: | ---: |
| [agent/agent\_runtime\_helpers.py](/agent/agent_runtime_helpers.py) | Python | 10 | 0 | 0 | 10 |
| [agent/tool\_dispatch\_helpers.py](/agent/tool_dispatch_helpers.py) | Python | 52 | -49 | 24 | 27 |
| [agent/tool\_executor.py](/agent/tool_executor.py) | Python | 13 | 0 | 0 | 13 |
| [hermes\_cli/plugins.py](/hermes_cli/plugins.py) | Python | 9 | 0 | 1 | 10 |
| [model\_tools.py](/model_tools.py) | Python | 6 | 0 | 0 | 6 |
| [plugins/team\_policy/\_\_init\_\_.py](/plugins/team_policy/__init__.py) | Python | 15 | 8 | 12 | 35 |
| [plugins/team\_policy/plugin.yaml](/plugins/team_policy/plugin.yaml) | YAML | 9 | 0 | 1 | 10 |
| [scripts/team-cloud-foundation-smoke.sh](/scripts/team-cloud-foundation-smoke.sh) | Shell Script | 5 | 0 | 0 | 5 |
| [scripts/team-cloud-import-sessiondb.py](/scripts/team-cloud-import-sessiondb.py) | Python | 37 | 2 | 12 | 51 |
| [scripts/team-cloud-memory-perf-baseline.py](/scripts/team-cloud-memory-perf-baseline.py) | Python | 17 | 2 | 11 | 30 |
| [teamDoc/GADoc/P2-21-memory-performance-baseline.md](/teamDoc/GADoc/P2-21-memory-performance-baseline.md) | Markdown | 31 | 0 | 12 | 43 |
| [teamDoc/GADoc/P2-22-sessiondb-import.md](/teamDoc/GADoc/P2-22-sessiondb-import.md) | Markdown | 33 | 0 | 12 | 45 |
| [teamDoc/GADoc/P2-23-memory-runtime-docs.md](/teamDoc/GADoc/P2-23-memory-runtime-docs.md) | Markdown | 87 | 0 | 32 | 119 |
| [teamDoc/GADoc/P3-01-tool-risk-taxonomy.md](/teamDoc/GADoc/P3-01-tool-risk-taxonomy.md) | Markdown | 38 | 0 | 14 | 52 |
| [teamDoc/GADoc/P3-02-team-tool-policy-hook.md](/teamDoc/GADoc/P3-02-team-tool-policy-hook.md) | Markdown | 45 | 0 | 16 | 61 |
| [teamDoc/GADoc/artifacts/memory-performance-baseline-v0.json](/teamDoc/GADoc/artifacts/memory-performance-baseline-v0.json) | JSON | 54 | 0 | 1 | 55 |
| [teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json](/teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json) | JSON | 20 | 0 | 0 | 20 |
| [teamDoc/GADoc/artifacts/tool-risk-taxonomy-v0.json](/teamDoc/GADoc/artifacts/tool-risk-taxonomy-v0.json) | JSON | 80 | 0 | 1 | 81 |
| [teamDoc/GALog/2026-05-22-p2-20-isolation-test-suite.md](/teamDoc/GALog/2026-05-22-p2-20-isolation-test-suite.md) | Markdown | 3 | 0 | 0 | 3 |
| [teamDoc/GALog/2026-05-22-p2-21-memory-performance-baseline.md](/teamDoc/GALog/2026-05-22-p2-21-memory-performance-baseline.md) | Markdown | 29 | 0 | 10 | 39 |
| [teamDoc/GALog/2026-05-22-p2-22-sessiondb-import.md](/teamDoc/GALog/2026-05-22-p2-22-sessiondb-import.md) | Markdown | 28 | 0 | 10 | 38 |
| [teamDoc/GALog/2026-05-22-p2-23-memory-runtime-docs.md](/teamDoc/GALog/2026-05-22-p2-23-memory-runtime-docs.md) | Markdown | 25 | 0 | 10 | 35 |
| [teamDoc/GALog/2026-05-22-p2-estimate-reconciliation.md](/teamDoc/GALog/2026-05-22-p2-estimate-reconciliation.md) | Markdown | 14 | 0 | 8 | 22 |
| [teamDoc/GALog/2026-05-22-p3-01-tool-risk-taxonomy.md](/teamDoc/GALog/2026-05-22-p3-01-tool-risk-taxonomy.md) | Markdown | 27 | 0 | 10 | 37 |
| [teamDoc/GALog/2026-05-22-p3-02-team-tool-policy-hook.md](/teamDoc/GALog/2026-05-22-p3-02-team-tool-policy-hook.md) | Markdown | 32 | 0 | 10 | 42 |
| [teamDoc/GAStep/01-work-package-register.md](/teamDoc/GAStep/01-work-package-register.md) | Markdown | 0 | 0 | -1 | -1 |
| [team\_cloud/memory/performance.py](/team_cloud/memory/performance.py) | Python | 53 | 2 | 10 | 65 |
| [team\_cloud/sessiondb\_import.py](/team_cloud/sessiondb_import.py) | Python | 145 | 12 | 28 | 185 |
| [team\_cloud/tool\_policy.py](/team_cloud/tool_policy.py) | Python | 184 | 4 | 25 | 213 |
| [team\_cloud/tool\_risk.py](/team_cloud/tool_risk.py) | Python | 110 | 2 | 17 | 129 |
| [tests/team\_cloud/test\_memory\_performance\_baseline.py](/tests/team_cloud/test_memory_performance_baseline.py) | Python | 32 | 0 | 14 | 46 |
| [tests/team\_cloud/test\_memory\_runtime\_docs.py](/tests/team_cloud/test_memory_runtime_docs.py) | Python | 36 | 0 | 13 | 49 |
| [tests/team\_cloud/test\_platform\_foundation\_suite.py](/tests/team_cloud/test_platform_foundation_suite.py) | Python | 5 | 0 | 0 | 5 |
| [tests/team\_cloud/test\_sessiondb\_import.py](/tests/team_cloud/test_sessiondb_import.py) | Python | 132 | 0 | 22 | 154 |
| [tests/team\_cloud/test\_team\_tool\_policy\_hook.py](/tests/team_cloud/test_team_tool_policy_hook.py) | Python | 124 | 0 | 38 | 162 |
| [tests/team\_cloud/test\_tool\_risk\_taxonomy.py](/tests/team_cloud/test_tool_risk_taxonomy.py) | Python | 47 | 0 | 15 | 62 |

[Summary](results.md) / [Details](details.md) / [Diff Summary](diff.md) / Diff Details