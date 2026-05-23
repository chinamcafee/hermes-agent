# P5-07 Release notes

日期：2026-05-23
状态：Implemented
前置：`P5-03 安装指南`、`P5-06 Runbook 汇总`

## 目标

本步骤固定 Team Cloud GA release notes contract，覆盖 GA highlights、`breaking_changes`、`upgrade_notes`、`known_issues` 和发布证据链接。该文档面向发布、支持、客户成功和内部试点迁移。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/release_notes.py` | `build_release_notes_package()` 生成 release notes JSON contract。 |
| `scripts/team-cloud-release-notes.py` | 写出 release notes JSON artifact。 |
| `teamDoc/GADoc/artifacts/release/team-cloud-ga-release-notes-v0.json` | P5-07 release notes artifact。 |
| `tests/team_cloud/test_release_notes.py` | P5-07 contract 测试。 |

## Highlights

- `enterprise_team_cloud`：开箱即用企业版 Team Cloud 控制面。
- `two_tier_memory`：personal 与 team_shared 双层记忆。
- `local_memory_backup`：个人记忆定时备份、导出和恢复路径。
- `casdoor_spicedb_postgres_minio_stack`：固定 Casdoor + SpiceDB + PostgreSQL/pgvector + MinIO 架构。
- `tool_policy_and_audit`：高危工具策略、审批和审计。

## breaking_changes

| ID | 说明 |
| --- | --- |
| `casdoor_identity_required` | Web 和 API 访问需要 Casdoor-backed identity。 |
| `team_scoped_memory` | 记忆读写必须带 org/team/member 上下文。 |
| `tool_policy_enforced` | 高危工具默认进入 TeamToolPolicyHook 和 audit gate。 |

## upgrade_notes

| ID | 说明 |
| --- | --- |
| `compose` | 本地 GA 安装使用 `deploy/team-cloud/compose.yaml`。 |
| `helm` | Kubernetes 安装使用 `deploy/team-cloud/helm/hermes-team-cloud/Chart.yaml`。 |
| `offline_bundle` | 离线安装必须携带 manifest、镜像和 checksums。 |
| `migration_checksums` | 升级和回滚前后都要校验 SQL migration checksums。 |

## known_issues

| ID | Severity | GA blocking | 说明 |
| --- | --- | --- | --- |
| `helm_lint_not_run_locally` | P3 | false | 本地环境可能没有 Helm；chart contract 已由静态测试覆盖。 |
| `external_sso_variants_post_ga` | P3 | false | GA 默认只承诺 Casdoor-backed SSO，其他 IdP 变体进入 Post-GA。 |

## Evidence

| ID | Artifact |
| --- | --- |
| `final_security_review` | `teamDoc/GADoc/artifacts/security/team-cloud-final-security-review-v0.json` |
| `sbom_license` | `teamDoc/GADoc/artifacts/release/team-cloud-sbom-license-v0.json` |
| `install_guide` | `teamDoc/GADoc/artifacts/release/team-cloud-install-guide-v0.json` |
| `runbook_summary` | `teamDoc/GADoc/artifacts/release/team-cloud-runbook-summary-v0.json` |

## 运行

```bash
scripts/team-cloud-release-notes.py --output teamDoc/GADoc/artifacts/release/team-cloud-ga-release-notes-v0.json
```

## 验证

```bash
scripts/run_tests.sh tests/team_cloud/test_release_notes.py
scripts/run_tests.sh tests/team_cloud/test_release_notes.py tests/team_cloud/test_install_guide.py tests/team_cloud/test_runbook_summary.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/ruff check team_cloud/release_notes.py scripts/team-cloud-release-notes.py tests/team_cloud/test_release_notes.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m py_compile team_cloud/release_notes.py scripts/team-cloud-release-notes.py tests/team_cloud/test_release_notes.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m json.tool teamDoc/GADoc/artifacts/release/team-cloud-ga-release-notes-v0.json >/dev/null
scripts/team-cloud-foundation-smoke.sh
```
