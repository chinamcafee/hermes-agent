from __future__ import annotations

from pathlib import Path


WEB_SHELL = Path("deploy/team-cloud/web-shell/index.html")


def test_admin_ux_final_exposes_empty_permission_and_bulk_confirm_surfaces():
    html = WEB_SHELL.read_text(encoding="utf-8")

    for expected in (
        'id="teams-empty-state"',
        'id="members-empty-state"',
        'id="audit-empty-state"',
        'id="usage-empty-state"',
        'id="chat-empty-state"',
        'class="empty-state"',
        'id="teams-permission-state"',
        'id="members-permission-state"',
        'id="audit-permission-state"',
        'id="usage-permission-state"',
        'id="members-bulk-disable"',
        'id="members-bulk-confirm"',
        'role="dialog"',
        'aria-modal="true"',
        'id="members-bulk-confirm-cancel"',
        'id="members-bulk-confirm-apply"',
    ):
        assert expected in html


def test_admin_ux_final_wires_helpers_without_native_confirm():
    html = WEB_SHELL.read_text(encoding="utf-8")

    for expected in (
        "renderEmptyState",
        "setEmptyState",
        "showPermissionState",
        "clearPermissionState",
        "updateMemberBulkControls",
        "openMembersBulkConfirm",
        "closeMembersBulkConfirm",
        "bulkDisableMembers",
        "selectedMemberIds",
        "membersBulkConfirm",
        "membersBulkDisableButton",
        "member-select",
        "permissionStateFromError",
    ):
        assert expected in html

    assert "window.confirm" not in html


def test_foundation_smoke_includes_admin_ux_final_check():
    content = Path("scripts/team-cloud-foundation-smoke.sh").read_text(encoding="utf-8")

    assert "tests/team_cloud/test_admin_ux_final.py" in content
