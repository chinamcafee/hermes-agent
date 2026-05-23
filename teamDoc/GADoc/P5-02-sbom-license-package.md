# P5-02 SBOM 和许可证包

日期：2026-05-23
状态：Implemented
前置：`P5-01 最终安全评审`

## 目标

本步骤固定 GA 发布所需的 SBOM 和 license_report contract，覆盖 Casdoor、SpiceDB、PostgreSQL、pgvector、MinIO 以及 Python 客户端依赖。

MinIO AGPL-3.0 是本包的重点说明项：发布包必须包含 source offer、网络服务源码可用性审查、客户告知、商业授权路径和 S3-compatible replacement path。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/sbom_license.py` | `build_sbom_license_package()` 生成 SBOM/license package。 |
| `scripts/team-cloud-sbom-license.py` | 写出 SBOM/license JSON artifact。 |
| `teamDoc/GADoc/artifacts/release/team-cloud-sbom-license-v0.json` | P5-02 SBOM/license artifact。 |
| `tests/team_cloud/test_sbom_license_package.py` | P5-02 contract 测试。 |

## license_report

- AGPL：MinIO。
- Apache-2.0：Casdoor、SpiceDB、authzed、casdoor、minio SDK。
- PostgreSQL License：PostgreSQL、pgvector。
- LGPL non-default：psycopg，不进入默认 runtime 依赖。

## risk_closures

- `RISK-001`：MinIO AGPL-3.0 obligations documented。
- `RISK-002`：MinIO image/source pin 和 replacement path documented。
- `RISK-012`：SBOM/license report generated。

## 运行

```bash
scripts/team-cloud-sbom-license.py --output teamDoc/GADoc/artifacts/release/team-cloud-sbom-license-v0.json
```

## 验证

```bash
scripts/run_tests.sh tests/team_cloud/test_sbom_license_package.py
scripts/run_tests.sh tests/team_cloud/test_sbom_license_package.py tests/team_cloud/test_final_security_review.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/ruff check team_cloud/sbom_license.py scripts/team-cloud-sbom-license.py tests/team_cloud/test_sbom_license_package.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m py_compile team_cloud/sbom_license.py scripts/team-cloud-sbom-license.py tests/team_cloud/test_sbom_license_package.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m json.tool teamDoc/GADoc/artifacts/release/team-cloud-sbom-license-v0.json >/dev/null
scripts/team-cloud-foundation-smoke.sh
```
