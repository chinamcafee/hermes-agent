# P4-15 i18n/accessibility pass

日期：2026-05-23
状态：Implemented
前置：`P3-22 Admin UX 收尾`

## 目标

本步骤固定 Team Cloud web shell 的关键中英文文案和键盘可用性 contract，覆盖 `supported_locales`、`critical_copy`、`keyboard_paths` 和 `wcag_checks`。

实现范围限定在 repo shipped web shell：新增 skip link、英文/简体中文语言切换、admin tabs roving focus、bulk confirm Escape 关闭路径和可见 focus 样式。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/i18n_accessibility.py` | `build_i18n_accessibility_pass()` 生成 i18n/accessibility contract。 |
| `scripts/team-cloud-i18n-accessibility.py` | 写出 i18n/accessibility JSON artifact。 |
| `teamDoc/GADoc/artifacts/pilot/team-cloud-i18n-accessibility-v0.json` | P4-15 i18n/accessibility artifact。 |
| `deploy/team-cloud/web-shell/index.html` | Web shell skip link、language toggle、tab 键盘和 Escape 行为。 |
| `tests/team_cloud/test_i18n_accessibility.py` | P4-15 contract 测试。 |

## 运行

```bash
scripts/team-cloud-i18n-accessibility.py --output teamDoc/GADoc/artifacts/pilot/team-cloud-i18n-accessibility-v0.json
```

## 验证

```bash
scripts/run_tests.sh tests/team_cloud/test_i18n_accessibility.py
scripts/run_tests.sh tests/team_cloud/test_i18n_accessibility.py tests/team_cloud/test_admin_ux_final.py tests/team_cloud/test_web_admin_pages.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/ruff check team_cloud/i18n_accessibility.py scripts/team-cloud-i18n-accessibility.py tests/team_cloud/test_i18n_accessibility.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m py_compile team_cloud/i18n_accessibility.py scripts/team-cloud-i18n-accessibility.py tests/team_cloud/test_i18n_accessibility.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m json.tool teamDoc/GADoc/artifacts/pilot/team-cloud-i18n-accessibility-v0.json >/dev/null
scripts/team-cloud-foundation-smoke.sh
```
