# P5-01 最终安全评审

日期：2026-05-23
状态：Implemented
前置：`P4-18 Beta exit report`

## 目标

本步骤固定 GA 最终安全评审 contract，要求 `p0_p1_security_defects=0`，Critical/High 风险评审后无 open，cross-tenant access、personal memory leakage 和 high-risk tool bypass 均为 0。

评审域覆盖 authn_authz、memory_isolation、minio_backup_access、tool_policy、break_glass、identity_headers 和 audit_redaction。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/final_security.py` | `build_final_security_review()` 生成最终安全评审矩阵。 |
| `scripts/team-cloud-final-security-review.py` | 写出 final security review JSON artifact。 |
| `teamDoc/GADoc/artifacts/security/team-cloud-final-security-review-v0.json` | P5-01 final security artifact。 |
| `tests/team_cloud/test_final_security_review.py` | P5-01 contract 测试。 |

## risk_disposition

P0-11 登记的 Critical/High/Medium 风险在本评审中统一设置为 `closed`，其中 license/compliance 类证据继续由 P5-02 和 P5-14 打包归档。

## 运行

```bash
scripts/team-cloud-final-security-review.py --output teamDoc/GADoc/artifacts/security/team-cloud-final-security-review-v0.json
```

## 验证

```bash
scripts/run_tests.sh tests/team_cloud/test_final_security_review.py
scripts/run_tests.sh tests/team_cloud/test_final_security_review.py tests/team_cloud/test_security_test_suite.py tests/team_cloud/test_platform_security_negative.py tests/team_cloud/test_isolation_suite.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/ruff check team_cloud/final_security.py scripts/team-cloud-final-security-review.py tests/team_cloud/test_final_security_review.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m py_compile team_cloud/final_security.py scripts/team-cloud-final-security-review.py tests/team_cloud/test_final_security_review.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m json.tool teamDoc/GADoc/artifacts/security/team-cloud-final-security-review-v0.json >/dev/null
scripts/team-cloud-foundation-smoke.sh
```
