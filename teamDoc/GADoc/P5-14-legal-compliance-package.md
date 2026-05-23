# P5-14 Legal/compliance package

日期：2026-05-23
状态：Implemented
前置：`P5-02`、`P5-01`、`P3-20`

## 目标

本步骤固定 Team Cloud GA legal/compliance package，汇总 SBOM、许可证、数据治理和安全证据。该包不替代正式法务意见，而是把 GA 发布所需证据固定为可审查 artifact，确保许可证义务、MinIO AGPL-3.0 notice、数据导出/删除/保留控制和 final security review 形成闭环。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/legal_compliance.py` | `build_legal_compliance_package()` 生成 legal/compliance JSON contract。 |
| `scripts/team-cloud-legal-compliance.py` | 写出 legal/compliance JSON artifact。 |
| `teamDoc/GADoc/artifacts/release/team-cloud-legal-compliance-v0.json` | P5-14 legal/compliance artifact。 |
| `tests/team_cloud/test_legal_compliance_package.py` | P5-14 contract 测试。 |

## 证据包

| Evidence | 来源 |
| --- | --- |
| `sbom_license` | `teamDoc/GADoc/artifacts/release/team-cloud-sbom-license-v0.json`、`P5-02-sbom-license-package.md` |
| `minio_agpl_notice` | MinIO AGPL-3.0 obligations：source offer、network service source availability、customer notice |
| `final_security_review` | `teamDoc/GADoc/artifacts/security/team-cloud-final-security-review-v0.json`、`P5-01-final-security-review.md` |
| `data_governance` | `P3-20-data-governance-runbooks.md` |
| `privacy_export_delete_retention` | `P3-10-org-export.md`、`P3-11-deletion-request.md`、`P3-13-retention-policies.md` |

## Review signoffs

- `legal_review`
- `security_review`
- `data_protection_review`
- `release_owner_review`

## Acceptance thresholds

- `unknown_licenses == 0`
- `missing_license_notices == 0`
- `open_critical_or_high_security_findings == 0`
- `uncovered_privacy_controls == 0`

## 运行

```bash
scripts/team-cloud-legal-compliance.py --output teamDoc/GADoc/artifacts/release/team-cloud-legal-compliance-v0.json
```

## 验证

```bash
scripts/run_tests.sh tests/team_cloud/test_legal_compliance_package.py
scripts/run_tests.sh tests/team_cloud/test_legal_compliance_package.py tests/team_cloud/test_sbom_license_package.py tests/team_cloud/test_final_security_review.py tests/team_cloud/test_data_governance_docs.py tests/team_cloud/test_org_export.py tests/team_cloud/test_deletion_request.py tests/team_cloud/test_retention_policies.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/ruff check team_cloud/legal_compliance.py scripts/team-cloud-legal-compliance.py tests/team_cloud/test_legal_compliance_package.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m py_compile team_cloud/legal_compliance.py scripts/team-cloud-legal-compliance.py tests/team_cloud/test_legal_compliance_package.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m json.tool teamDoc/GADoc/artifacts/release/team-cloud-legal-compliance-v0.json >/dev/null
scripts/team-cloud-foundation-smoke.sh
```
