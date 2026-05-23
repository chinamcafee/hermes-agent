# P5-14 Legal/compliance package 工作日志

## 背景

- 工作包：`P5-14 | Legal/compliance package | SBOM、许可证、数据治理和安全证据汇总 | P5-02/P5-01/P3-20 | 1`
- 当前阶段：P5 GA 发布，P5-01 到 P5-13 已完成。

## 执行计划

1. 用 contract 测试定义 legal/compliance package 的证据清单、许可证/SBOM、数据治理和安全材料。
2. 新增 legal compliance builder 和生成脚本。
3. 新增 P5-14 文档和 JSON artifact。
4. 将 legal/compliance package 注册到 smoke 矩阵和 foundation smoke。
5. 运行红灯、绿灯、关联回归、静态检查和完整 smoke。

## 实时记录

- 2026-05-23：P5-14 已在进度表中标记为 In Progress，准备按 TDD 红绿循环推进。
- 2026-05-23：新增红灯测试 `tests/team_cloud/test_legal_compliance_package.py`，确认失败原因为缺失 `team_cloud.legal_compliance`。
- 2026-05-23：新增 `team_cloud/legal_compliance.py`、`scripts/team-cloud-legal-compliance.py`、`teamDoc/GADoc/P5-14-legal-compliance-package.md` 和 `teamDoc/GADoc/artifacts/release/team-cloud-legal-compliance-v0.json`。
- 2026-05-23：将 `legal_compliance_package` 注册到 `scripts/team-cloud-foundation-smoke.sh`、`tests/team_cloud/test_platform_foundation_suite.py` 和 `teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json`。
- 2026-05-23：验证通过：
  - `scripts/run_tests.sh tests/team_cloud/test_legal_compliance_package.py`：2 tests passed。
  - `scripts/run_tests.sh tests/team_cloud/test_legal_compliance_package.py tests/team_cloud/test_sbom_license_package.py tests/team_cloud/test_final_security_review.py tests/team_cloud/test_data_governance_docs.py tests/team_cloud/test_org_export.py tests/team_cloud/test_deletion_request.py tests/team_cloud/test_retention_policies.py tests/team_cloud/test_platform_foundation_suite.py`：18 tests passed。
  - `venv/bin/ruff check team_cloud/legal_compliance.py scripts/team-cloud-legal-compliance.py tests/team_cloud/test_legal_compliance_package.py tests/team_cloud/test_platform_foundation_suite.py`：All checks passed。
  - `venv/bin/python -m py_compile team_cloud/legal_compliance.py scripts/team-cloud-legal-compliance.py tests/team_cloud/test_legal_compliance_package.py tests/team_cloud/test_platform_foundation_suite.py`：通过。
  - `venv/bin/python -m json.tool teamDoc/GADoc/artifacts/release/team-cloud-legal-compliance-v0.json >/dev/null && venv/bin/python -m json.tool teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json >/dev/null`：通过。
  - `scripts/team-cloud-foundation-smoke.sh`：100 files, 310 tests passed, 0 failed。
  - `git diff --check -- ...`：通过。
