# P5-03 安装指南 工作日志

## 背景

- 工作包：`P5-03 | 安装指南 | compose/helm/offline install、环境检查、首次登录 | P5-02 | 1.5`
- 当前阶段：P5 GA 发布，P5-01 到 P5-02 已完成。

## 执行计划

1. 用 contract 测试定义安装指南、artifact、脚本和 smoke 注册。
2. 新增 install guide builder 和生成脚本。
3. 新增 P5-03 文档和 JSON artifact。
4. 运行红灯、绿灯、回归、静态检查和完整 smoke。

## 实时记录

- 2026-05-23：P5-03 已在进度表中标记为 In Progress，准备按 TDD 红绿循环推进。
- 2026-05-23：新增红灯 contract 测试，覆盖 compose/helm/offline bundle 安装路径、preflight、first_login、health checks、troubleshooting、artifact、文档和 smoke 注册。
- 2026-05-23：红灯验证 `scripts/run_tests.sh tests/team_cloud/test_install_guide.py` 失败，2 个测试均因缺少 `team_cloud.install_guide` 报 `ModuleNotFoundError`，失败原因符合预期。
- 2026-05-23：新增 `team_cloud/install_guide.py`、`scripts/team-cloud-install-guide.py`、`teamDoc/GADoc/P5-03-install-guide.md`，并在 foundation smoke script、suite 测试和 smoke matrix 中注册 `install_guide`。
- 2026-05-23：运行 `scripts/team-cloud-install-guide.py --output teamDoc/GADoc/artifacts/release/team-cloud-install-guide-v0.json` 写出 release artifact。
- 2026-05-23：绿灯验证 `scripts/run_tests.sh tests/team_cloud/test_install_guide.py` 通过，1 个文件、2 个测试通过。
- 2026-05-23：相关回归 `scripts/run_tests.sh tests/team_cloud/test_install_guide.py tests/team_cloud/test_deployment_docs.py tests/team_cloud/test_compose_hardening.py tests/team_cloud/test_helm_chart.py tests/team_cloud/test_offline_bundle.py tests/team_cloud/test_platform_foundation_suite.py` 通过，6 个文件、16 个测试通过。
- 2026-05-23：静态检查通过：`venv/bin/ruff check team_cloud/install_guide.py scripts/team-cloud-install-guide.py tests/team_cloud/test_install_guide.py tests/team_cloud/test_platform_foundation_suite.py`。
- 2026-05-23：编译检查通过：`venv/bin/python -m py_compile team_cloud/install_guide.py scripts/team-cloud-install-guide.py tests/team_cloud/test_install_guide.py tests/team_cloud/test_platform_foundation_suite.py`。
- 2026-05-23：JSON 校验通过：`teamDoc/GADoc/artifacts/release/team-cloud-install-guide-v0.json` 和 `teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json`。
- 2026-05-23：空白检查 `git diff --check -- <P5-03 touched files>` 通过。
- 2026-05-23：完整门禁 `scripts/team-cloud-foundation-smoke.sh` 通过，89 个文件、288 个测试通过，0 failed。
