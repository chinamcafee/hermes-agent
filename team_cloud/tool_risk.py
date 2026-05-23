"""Tool risk taxonomy for Team Cloud policy hooks."""

from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Any, Literal, get_args


RiskCategory = Literal["safe", "network", "file", "terminal", "destructive", "secret"]
RISK_CATEGORIES: tuple[RiskCategory, ...] = get_args(RiskCategory)
APPROVAL_REQUIRED: tuple[RiskCategory, ...] = ("terminal", "destructive", "secret")

TOOL_DEFAULTS: dict[str, RiskCategory] = {
    "memory": "safe",
    "todo": "safe",
    "clarify": "safe",
    "skills_list": "safe",
    "skill_view": "safe",
    "skill_manage": "file",
    "web_search": "network",
    "web_extract": "network",
    "x_search": "network",
    "browser_navigate": "network",
    "browser_snapshot": "network",
    "browser_click": "network",
    "browser_type": "network",
    "browser_scroll": "network",
    "browser_back": "network",
    "browser_press": "network",
    "browser_get_images": "network",
    "browser_vision": "network",
    "browser_console": "network",
    "browser_cdp": "network",
    "browser_dialog": "network",
    "send_message": "network",
    "ha_list_entities": "network",
    "ha_get_state": "network",
    "ha_list_services": "network",
    "ha_call_service": "destructive",
    "read_file": "file",
    "write_file": "file",
    "patch": "file",
    "search_files": "file",
    "vision_analyze": "file",
    "image_generate": "file",
    "text_to_speech": "file",
    "session_search": "safe",
    "terminal": "terminal",
    "process": "terminal",
    "execute_code": "terminal",
    "delegate_task": "terminal",
    "cronjob": "terminal",
    "computer_use": "terminal",
    "kanban_show": "safe",
    "kanban_list": "safe",
    "kanban_complete": "safe",
    "kanban_block": "safe",
    "kanban_heartbeat": "safe",
    "kanban_comment": "safe",
    "kanban_create": "safe",
    "kanban_link": "safe",
    "kanban_unblock": "safe",
}

_SECRET_KEY_RE = re.compile(
    r"(api[_-]?key|token|password|passwd|secret|credential|private[_-]?key)",
    re.IGNORECASE,
)
_DESTRUCTIVE_COMMAND_RE = re.compile(
    r"(\brm\s+-[^\n]*r|\bsudo\b|\bdd\s+if=|\bmkfs\b|\bdiskutil\b|"
    r"\bdrop\s+table\b|\btruncate\s+table\b)",
    re.IGNORECASE,
)


def classify_tool_call(tool_name: str, args: Mapping[str, Any] | None = None) -> RiskCategory:
    """Classify a tool call before policy enforcement."""
    normalized_name = str(tool_name or "").strip()
    normalized_args = dict(args or {})
    if _contains_secret_material(normalized_args):
        return "secret"
    if normalized_name == "terminal" and _looks_destructive_command(normalized_args):
        return "destructive"
    return TOOL_DEFAULTS.get(normalized_name, "safe")


def risk_requires_approval(category: RiskCategory | str) -> bool:
    return str(category) in APPROVAL_REQUIRED


def build_tool_risk_taxonomy() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "name": "tool-risk-taxonomy-v0",
        "categories": RISK_CATEGORIES,
        "approval_required": list(APPROVAL_REQUIRED),
        "tool_defaults": dict(TOOL_DEFAULTS),
        "escalation_rules": [
            {
                "name": "secret_argument_key",
                "category": "secret",
                "description": "Any argument key containing token, password, secret, credential, private_key, or api_key.",
            },
            {
                "name": "terminal_destructive_command",
                "category": "destructive",
                "description": "Terminal commands matching rm -r, sudo, dd if=, mkfs, diskutil, drop table, or truncate table.",
            },
        ],
    }


def _contains_secret_material(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if _SECRET_KEY_RE.search(str(key)):
                return True
            if _contains_secret_material(nested):
                return True
    elif isinstance(value, list | tuple):
        return any(_contains_secret_material(item) for item in value)
    return False


def _looks_destructive_command(args: Mapping[str, Any]) -> bool:
    command = args.get("command") or args.get("cmd") or ""
    return bool(_DESTRUCTIVE_COMMAND_RE.search(str(command)))
