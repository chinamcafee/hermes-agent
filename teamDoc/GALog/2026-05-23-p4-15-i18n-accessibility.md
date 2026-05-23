# P4-15 i18n/accessibility pass 工作日志

## 背景

- 工作包：`P4-15 | i18n/accessibility pass | 中文/英文关键文案、键盘可用性 | P3-22 | 1`
- 当前阶段：P4 Beta 验证，P4-01 到 P4-14 已完成。

## 执行计划

1. 用 contract 测试定义 i18n/accessibility checklist、artifact、脚本和 smoke 注册。
2. 新增 i18n/accessibility builder 和生成脚本。
3. 新增 P4-15 文档和 JSON artifact。
4. 运行红灯、绿灯、回归、静态检查和完整 smoke。

## 实时记录

- 2026-05-23：P4-15 已在进度表中标记为 In Progress，准备按 TDD 红绿循环推进。
- 2026-05-23：新增红灯 contract 测试，覆盖 i18n/accessibility builder、web shell skip link、语言切换、tab 键盘路径、artifact、文档和 smoke 注册。
- 2026-05-23：红灯验证已执行，`scripts/run_tests.sh tests/team_cloud/test_i18n_accessibility.py` 出现 3 个预期失败，指向 `team_cloud.i18n_accessibility`、web shell i18n/accessibility controls 和 artifact/smoke 注册缺口。
- 2026-05-23：新增 `team_cloud/i18n_accessibility.py`、`scripts/team-cloud-i18n-accessibility.py`、`tests/team_cloud/test_i18n_accessibility.py`、`teamDoc/GADoc/P4-15-i18n-accessibility.md` 和 `teamDoc/GADoc/artifacts/pilot/team-cloud-i18n-accessibility-v0.json`。
- 2026-05-23：更新 `deploy/team-cloud/web-shell/index.html`，加入 skip link、英文/简体中文语言切换、admin tabs `role=tab`/`aria-selected`/roving focus、bulk confirm Escape 关闭和可见 focus 样式。
- 2026-05-23：已把 P4-15 纳入 `scripts/team-cloud-foundation-smoke.sh`、`tests/team_cloud/test_platform_foundation_suite.py` 和 `teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json`。
- 2026-05-23：生成脚本验证通过，`scripts/team-cloud-i18n-accessibility.py --output teamDoc/GADoc/artifacts/pilot/team-cloud-i18n-accessibility-v0.json` 输出 `status=written`。
- 2026-05-23：目标测试通过，`scripts/run_tests.sh tests/team_cloud/test_i18n_accessibility.py` 通过 1 个文件 / 3 个测试。
- 2026-05-23：回归验证通过，`scripts/run_tests.sh tests/team_cloud/test_i18n_accessibility.py tests/team_cloud/test_admin_ux_final.py tests/team_cloud/test_web_admin_pages.py tests/team_cloud/test_web_login_shell.py tests/team_cloud/test_platform_foundation_suite.py` 通过 5 个文件 / 14 个测试。
- 2026-05-23：静态验证通过，`venv/bin/ruff check ...`、`venv/bin/python -m py_compile ...`、JSON artifact 检查和 `git diff --check` 均为 exit 0。
- 2026-05-23：完整 foundation smoke 通过，`scripts/team-cloud-foundation-smoke.sh` 覆盖 83 个文件 / 276 个测试。
