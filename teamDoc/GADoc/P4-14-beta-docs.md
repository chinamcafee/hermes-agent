# P4-14 Beta 文档

日期：2026-05-23
状态：Implemented
前置：`P4-10 Pilot onboarding`

## 目标

本步骤固定 Beta 文档包 contract，面向 pilot admin、SRE、support、release manager 和试点成员，覆盖安装 quickstart、pilot onboarding、feedback_and_triage_guide、known_issues 和 beta_exit_checklist。

Beta 文档包把 P4-01 到 P4-13 的部署、观测、压测、安全、备份恢复、升级回滚、成本配额和 chaos drill 证据串联到一个 pilot 可执行索引。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/beta_docs.py` | `build_beta_documentation_package()` 生成 Beta 文档包 contract。 |
| `scripts/team-cloud-beta-docs.py` | 写出 Beta docs JSON artifact。 |
| `teamDoc/GADoc/artifacts/pilot/team-cloud-beta-docs-v0.json` | P4-14 Beta 文档包 artifact。 |
| `tests/team_cloud/test_beta_docs.py` | P4-14 contract 测试。 |

## 文档包目录

| id | 内容 |
| --- | --- |
| `pilot_install_quickstart` | Compose、Helm、offline bundle 和 upgrade/rollback 的 pilot 安装入口。 |
| `pilot_onboarding_guide` | 3 个试点团队、成员导入、Gateway 平台、初始项目和两周运行节奏。 |
| `feedback_and_triage_guide` | 反馈字段、severity、SLA、release blocker 和升级通道。 |
| `known_issues` | Beta 限制、helm lint 本地依赖、restore drill live service 前置和生产数据导入窗口。 |
| `beta_exit_checklist` | 14 天试点、0 个 P0/P1、安全套件、备份恢复和 chaos action 收敛。 |

## 运行

```bash
scripts/team-cloud-beta-docs.py --output teamDoc/GADoc/artifacts/pilot/team-cloud-beta-docs-v0.json
```

## 验证

```bash
scripts/run_tests.sh tests/team_cloud/test_beta_docs.py
scripts/run_tests.sh tests/team_cloud/test_beta_docs.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/ruff check team_cloud/beta_docs.py scripts/team-cloud-beta-docs.py tests/team_cloud/test_beta_docs.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m py_compile team_cloud/beta_docs.py scripts/team-cloud-beta-docs.py tests/team_cloud/test_beta_docs.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m json.tool teamDoc/GADoc/artifacts/pilot/team-cloud-beta-docs-v0.json >/dev/null
scripts/team-cloud-foundation-smoke.sh
```
