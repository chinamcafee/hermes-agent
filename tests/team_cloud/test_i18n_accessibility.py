from __future__ import annotations

import json
import os
from pathlib import Path


ARTIFACT = Path("teamDoc/GADoc/artifacts/pilot/team-cloud-i18n-accessibility-v0.json")
DOC = Path("teamDoc/GADoc/P4-15-i18n-accessibility.md")
SCRIPT = Path("scripts/team-cloud-i18n-accessibility.py")
WEB_SHELL = Path("deploy/team-cloud/web-shell/index.html")
SMOKE_SCRIPT = Path("scripts/team-cloud-foundation-smoke.sh")
SMOKE_MATRIX = Path("teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json")


def test_i18n_accessibility_pass_defines_locale_keyboard_and_wcag_contract():
    from team_cloud.i18n_accessibility import build_i18n_accessibility_pass

    plan = build_i18n_accessibility_pass()
    copy_keys = {item["key"]: item["locales"] for item in plan["critical_copy"]}
    keyboard_paths = {item["id"] for item in plan["keyboard_paths"]}

    assert plan["schema_version"] == 1
    assert plan["name"] == "team-cloud-i18n-accessibility-v0"
    assert plan["supported_locales"] == ["en", "zh-CN"]
    assert {"sign_in", "team_console", "permission_denied", "empty_teams"} <= set(copy_keys)
    assert all({"en", "zh-CN"} <= set(locales) for locales in copy_keys.values())
    assert {
        "skip_to_main",
        "language_toggle",
        "admin_tab_roving_focus",
        "bulk_confirm_escape",
    } <= keyboard_paths
    assert "form_labels" in plan["wcag_checks"]
    assert "aria_live_status" in plan["wcag_checks"]
    assert "focus_visible" in plan["wcag_checks"]


def test_web_shell_exposes_language_toggle_skip_link_and_keyboard_tab_contract():
    html = WEB_SHELL.read_text(encoding="utf-8")

    for expected in (
        'class="skip-link"',
        'href="#main-content"',
        'id="main-content"',
        'tabindex="-1"',
        'class="language-toggle"',
        'aria-label="Language"',
        'data-locale="en"',
        'data-locale="zh-CN"',
        'data-i18n="team_console"',
        'data-i18n="sign_in"',
        'data-i18n-active',
        'role="tab"',
        'aria-selected="true"',
        'aria-controls="teams-panel"',
        'tabindex="0"',
        "I18N_MESSAGES",
        "setLocale",
        "applyTranslations",
        "handleAdminTabKeydown",
        "Escape",
    ):
        assert expected in html


def test_i18n_accessibility_artifact_script_docs_and_smoke_are_registered():
    from team_cloud.i18n_accessibility import build_i18n_accessibility_pass

    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    doc = DOC.read_text(encoding="utf-8")
    script = SCRIPT.read_text(encoding="utf-8")
    smoke = SMOKE_SCRIPT.read_text(encoding="utf-8")
    matrix = json.loads(SMOKE_MATRIX.read_text(encoding="utf-8"))
    domains = {entry["domain"] for entry in matrix["checks"]}

    assert artifact == build_i18n_accessibility_pass()
    assert os.access(SCRIPT, os.X_OK)
    assert "team-cloud-i18n-accessibility-v0.json" in script
    assert "supported_locales" in doc
    assert "keyboard_paths" in doc
    assert "wcag_checks" in doc
    assert "tests/team_cloud/test_i18n_accessibility.py" in smoke
    assert "i18n_accessibility" in domains
