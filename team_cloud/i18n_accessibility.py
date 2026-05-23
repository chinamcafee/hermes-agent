"""i18n and accessibility pass contract for Team Cloud Beta."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


_CRITICAL_COPY: tuple[dict[str, Any], ...] = (
    {
        "key": "skip_to_main",
        "locales": {"en": "Skip to main content", "zh-CN": "跳到主要内容"},
    },
    {
        "key": "sign_in",
        "locales": {"en": "Sign in with Casdoor", "zh-CN": "使用 Casdoor 登录"},
    },
    {
        "key": "team_console",
        "locales": {"en": "Team Console", "zh-CN": "团队控制台"},
    },
    {
        "key": "permission_denied",
        "locales": {
            "en": "Access denied for the selected organization or resource.",
            "zh-CN": "当前组织或资源无访问权限。",
        },
    },
    {
        "key": "empty_teams",
        "locales": {"en": "No teams available.", "zh-CN": "暂无团队。"},
    },
    {
        "key": "refresh_organizations",
        "locales": {"en": "Refresh organizations", "zh-CN": "刷新组织"},
    },
)

_KEYBOARD_PATHS: tuple[dict[str, str], ...] = (
    {
        "id": "skip_to_main",
        "target": "main-content",
        "behavior": "First focusable control jumps directly to the app content.",
    },
    {
        "id": "language_toggle",
        "target": "language-toggle",
        "behavior": "English and zh-CN buttons expose pressed state.",
    },
    {
        "id": "admin_tab_roving_focus",
        "target": "data-admin-tab",
        "behavior": "Arrow keys, Home, and End move focus and selected tab.",
    },
    {
        "id": "bulk_confirm_escape",
        "target": "members-bulk-confirm",
        "behavior": "Escape closes the bulk disable confirmation dialog.",
    },
)


def build_i18n_accessibility_pass() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "name": "team-cloud-i18n-accessibility-v0",
        "supported_locales": ["en", "zh-CN"],
        "critical_copy": deepcopy(list(_CRITICAL_COPY)),
        "keyboard_paths": deepcopy(list(_KEYBOARD_PATHS)),
        "wcag_checks": [
            "form_labels",
            "aria_live_status",
            "focus_visible",
            "tab_roles",
            "dialog_escape",
        ],
        "web_shell": "deploy/team-cloud/web-shell/index.html",
    }


__all__ = ["build_i18n_accessibility_pass"]
