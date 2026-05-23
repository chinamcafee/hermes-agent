# P5-02 SBOM 和许可证包 工作日志

## 背景

- 工作包：`P5-02 | SBOM 和许可证包 | 依赖清单、许可证、MinIO AGPL-3.0 说明 | P5-01 | 1.5`
- 当前阶段：P5 GA 发布，P5-01 已完成。

## 执行计划

1. 用 contract 测试定义 SBOM/license package、artifact、脚本和 smoke 注册。
2. 新增 SBOM/license builder 和生成脚本。
3. 新增 P5-02 文档和 JSON artifact。
4. 运行红灯、绿灯、回归、静态检查和完整 smoke。

## 实时记录

- 2026-05-23：P5-02 已在进度表中标记为 In Progress，准备按 TDD 红绿循环推进。
- 2026-05-23：新增红灯 contract 测试，覆盖核心组件 SBOM、license report、MinIO AGPL-3.0 义务、RISK-001/RISK-002/RISK-012 closure、artifact、文档和 smoke 注册。
- 2026-05-23：红灯验证已执行，`scripts/run_tests.sh tests/team_cloud/test_sbom_license_package.py` 出现 2 个预期失败，指向 `team_cloud.sbom_license` 缺失。
- 2026-05-23：新增 `team_cloud/sbom_license.py`、`scripts/team-cloud-sbom-license.py`、`tests/team_cloud/test_sbom_license_package.py`、`teamDoc/GADoc/P5-02-sbom-license-package.md` 和 `teamDoc/GADoc/artifacts/release/team-cloud-sbom-license-v0.json`。
- 2026-05-23：已把 P5-02 纳入 `scripts/team-cloud-foundation-smoke.sh`、`tests/team_cloud/test_platform_foundation_suite.py` 和 `teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json`。
- 2026-05-23：生成脚本验证通过，`scripts/team-cloud-sbom-license.py --output teamDoc/GADoc/artifacts/release/team-cloud-sbom-license-v0.json` 输出 `status=written`。
- 2026-05-23：目标测试通过，`scripts/run_tests.sh tests/team_cloud/test_sbom_license_package.py` 通过 1 个文件 / 2 个测试。
- 2026-05-23：回归验证通过，`scripts/run_tests.sh tests/team_cloud/test_sbom_license_package.py tests/team_cloud/test_final_security_review.py tests/team_cloud/test_platform_foundation_suite.py` 通过 3 个文件 / 7 个测试。
- 2026-05-23：静态验证通过，`venv/bin/ruff check ...`、`venv/bin/python -m py_compile ...`、JSON artifact 检查和 `git diff --check` 均为 exit 0。
- 2026-05-23：完整 foundation smoke 通过，`scripts/team-cloud-foundation-smoke.sh` 覆盖 88 个文件 / 286 个测试。
