# P4-08 Security test suite

日期：2026-05-23
状态：Implemented
前置：`P3 数据治理与权限硬化`

## 目标

本步骤固定 Team Cloud Beta 的统一安全负测矩阵。矩阵覆盖 P4 要求的伪造 token、错误 audience/issuer、禁用成员、跨 org memory query、prompt injection 诱导读取 personal memory、tool bypass、break-glass abuse、MinIO signed URL 越权。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/security_suite.py` | `build_security_test_suite()` 生成安全测试矩阵。 |
| `scripts/team-cloud-security-suite.py` | 写出安全测试 suite JSON artifact。 |
| `teamDoc/GADoc/artifacts/security/team-cloud-security-suite-v0.json` | P4-08 安全测试矩阵 artifact。 |
| `tests/team_cloud/test_security_test_suite.py` | P4-08 contract 测试。 |

## 攻击场景

| Case | 控制点 |
| --- | --- |
| `forged_casdoor_token` | JWKS signature verification、token redaction |
| `wrong_audience_issuer` | issuer/audience/expiry check |
| `disabled_member_access` | member active check、fail closed |
| `cross_org_memory_query` | org scope filter、SpiceDB memory read check |
| `prompt_injection_personal_memory_exfiltration` | context fencing、personal memory scope check |
| `tool_bypass_high_risk` | tool permission、approval required、fail closed |
| `break_glass_abuse` | two-person approval、short-lived grant、audit notification |
| `minio_signed_url_cross_org` | object manifest owner check、checksum validation |

## 运行

```bash
scripts/team-cloud-security-suite.py --output teamDoc/GADoc/artifacts/security/team-cloud-security-suite-v0.json
```

## 验证

```bash
scripts/run_tests.sh tests/team_cloud/test_security_test_suite.py
scripts/run_tests.sh tests/team_cloud/test_security_test_suite.py tests/team_cloud/test_platform_security_negative.py tests/team_cloud/test_jwt_middleware.py tests/team_cloud/test_isolation_suite.py tests/team_cloud/test_team_tool_policy_hook.py tests/team_cloud/test_tool_audit.py tests/team_cloud/test_break_glass.py tests/team_cloud/test_backup_storage.py tests/team_cloud/test_minio_manifest.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/ruff check team_cloud/security_suite.py scripts/team-cloud-security-suite.py tests/team_cloud/test_security_test_suite.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m py_compile team_cloud/security_suite.py scripts/team-cloud-security-suite.py tests/team_cloud/test_security_test_suite.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m json.tool teamDoc/GADoc/artifacts/security/team-cloud-security-suite-v0.json >/dev/null
scripts/team-cloud-foundation-smoke.sh
```
