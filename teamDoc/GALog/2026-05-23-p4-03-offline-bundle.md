# P4-03 Offline bundle 工作日志

## 背景

- 工作包：`P4-03 | Offline bundle | images、charts、checksums、install script | P4-02 | 2`
- 当前阶段：P4 Beta 验证，P4-01/P4-02 已完成。
- 设计依据：
  - Helm chart 位于 `deploy/team-cloud/helm/hermes-team-cloud/`。
  - Compose/Helm 均已固定镜像和本地部署 contract。

## 执行计划

1. 用静态 bundle contract 测试定义 manifest、镜像清单、checksum、build script 和 install script。
2. 创建 `deploy/team-cloud/offline/` manifest 和 install/readme 工件。
3. 创建 `scripts/team-cloud-offline-bundle.sh`，输出 chart archive、image list 和 checksum manifest。
4. 注册 foundation smoke 并更新 P4-03 文档。

## 实时记录

- 2026-05-23：P4-03 标记为 In Progress，开始按 TDD 红绿循环推进。
- 2026-05-23：红灯验证已执行，`scripts/run_tests.sh tests/team_cloud/test_offline_bundle.py` 出现 3 个预期失败，分别指向离线 manifest、bundle/install 脚本、README、文档和 smoke 注册缺口。
- 2026-05-23：新增 `deploy/team-cloud/offline/manifest.yaml`、`install.sh`、`README.md` 和 `scripts/team-cloud-offline-bundle.sh`，并将 P4-03 测试注册到 foundation smoke。
- 2026-05-23：绿灯验证通过，`scripts/run_tests.sh tests/team_cloud/test_offline_bundle.py` 结果为 1 个文件、3 个测试通过。
- 2026-05-23：相关回归通过，`scripts/run_tests.sh tests/team_cloud/test_offline_bundle.py tests/team_cloud/test_helm_chart.py tests/team_cloud/test_platform_foundation_suite.py` 结果为 3 个文件、9 个测试通过。
- 2026-05-23：静态验证通过，`venv/bin/ruff check ...`、`venv/bin/python -m py_compile ...`、`venv/bin/python -m json.tool teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json >/dev/null` 和 `git diff --check ...` 均为 exit 0。
- 2026-05-23：完整 foundation smoke 通过，`scripts/team-cloud-foundation-smoke.sh` 结果为 71 个文件、249 个测试通过。
