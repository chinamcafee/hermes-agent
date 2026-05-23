from __future__ import annotations

from pathlib import Path


WEB_SHELL = Path("deploy/team-cloud/web-shell/index.html")


def test_web_login_shell_contains_oidc_session_and_org_switcher():
    html = WEB_SHELL.read_text(encoding="utf-8")

    assert "/auth/oidc/authorize" in html
    assert "/auth/oidc/callback" in html
    assert "sessionStorage" in html
    assert "hermesTeamSession" in html
    assert "organization-switcher" in html
    assert "/api/organizations" in html
    assert "data-view=\"login\"" in html
    assert "data-view=\"app\"" in html
    assert "Local web shell for the P1 compose stack" not in html


def test_web_login_shell_has_operational_controls_and_error_states():
    html = WEB_SHELL.read_text(encoding="utf-8")

    assert "id=\"login-button\"" in html
    assert "id=\"logout-button\"" in html
    assert "id=\"refresh-organizations\"" in html
    assert "id=\"callback-status\"" in html
    assert "id=\"session-subject\"" in html
    assert "id=\"shell-error\"" in html
    assert "showError" in html
    assert "renderOrganizations" in html
