# P5-07 Release notes 工作日志

## 背景

- 工作包：`P5-07 | Release notes | breaking changes、upgrade notes、known issues | P5-03 | 0.5`
- 当前阶段：P5 GA 发布，P5-01 到 P5-06 已完成。

## 执行计划

1. 用 contract 测试定义 GA release notes、breaking changes、upgrade notes、known issues 和 artifact。
2. 新增 release notes builder 和生成脚本。
3. 新增 P5-07 文档和 JSON artifact。
4. 运行红灯、绿灯、回归、静态检查和完整 smoke。

## 实时记录

- 2026-05-23：P5-07 已在进度表中标记为 In Progress，准备按 TDD 红绿循环推进。
- 2026-05-23：新增红灯 contract 测试，覆盖 GA highlights、breaking_changes、upgrade_notes、known_issues、P5 证据链接、artifact、文档和 smoke 注册。
- 2026-05-23：红灯验证 `scripts/run_tests.sh tests/team_cloud/test_release_notes.py` 失败，2 个测试均因缺少 `team_cloud.release_notes` 报 `ModuleNotFoundError`，失败原因符合预期。
- 2026-05-23：新增 `team_cloud/release_notes.py`、`scripts/team-cloud-release-notes.py`、`teamDoc/GADoc/P5-07-release-notes.md`，并在 foundation smoke script、suite 测试和 smoke matrix 中注册 `release_notes`。
- 2026-05-23：运行 `scripts/team-cloud-release-notes.py --output teamDoc/GADoc/artifacts/release/team-cloud-ga-release-notes-v0.json` 写出 release artifact。
- 2026-05-23：绿灯验证 `scripts/run_tests.sh tests/team_cloud/test_release_notes.py` 通过，1 个文件、2 个测试通过。
- 2026-05-23：相关回归 `scripts/run_tests.sh tests/team_cloud/test_release_notes.py tests/team_cloud/test_install_guide.py tests/team_cloud/test_runbook_summary.py tests/team_cloud/test_platform_foundation_suite.py` 通过，4 个文件、9 个测试通过。
- 2026-05-23：静态检查通过：`venv/bin/ruff check team_cloud/release_notes.py scripts/team-cloud-release-notes.py tests/team_cloud/test_release_notes.py tests/team_cloud/test_platform_foundation_suite.py`。
- 2026-05-23：编译检查通过：`venv/bin/python -m py_compile team_cloud/release_notes.py scripts/team-cloud-release-notes.py tests/team_cloud/test_release_notes.py tests/team_cloud/test_platform_foundation_suite.py`。
- 2026-05-23：JSON 校验通过：`teamDoc/GADoc/artifacts/release/team-cloud-ga-release-notes-v0.json` 和 `teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json`。
- 2026-05-23：空白检查 `git diff --check -- <P5-07 touched files>` 通过。
- 2026-05-23：完整门禁 `scripts/team-cloud-foundation-smoke.sh` 通过，93 个文件、296 个测试通过，0 failed。
