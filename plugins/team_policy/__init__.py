"""Team Cloud tool policy plugin."""

from __future__ import annotations

import logging
from typing import Any

from utils import env_var_enabled


logger = logging.getLogger(__name__)

HERMES_TEAM_TOOL_POLICY_ENABLED = "HERMES_TEAM_TOOL_POLICY_ENABLED"


def register(ctx: Any) -> None:
    """Register the TeamToolPolicyHook when enterprise policy is enabled."""
    if not env_var_enabled(HERMES_TEAM_TOOL_POLICY_ENABLED):
        logger.debug("Team Cloud tool policy plugin loaded but not enabled")
        return

    from agent.team_tool_policy import TeamToolPolicyHook, build_default_approval_callback

    hook = TeamToolPolicyHook(
        authz_client=_build_authz_client(),
        approval_callback=build_default_approval_callback(),
    )
    ctx.register_hook("pre_tool_call", hook.pre_tool_call)


def _build_authz_client() -> Any:
    """Return the runtime SpiceDB client when one is wired by Team Cloud.

    P3-02 defines the fail-closed hook boundary. A concrete network transport
    is supplied by Team Cloud runtime wiring in later governance work; until
    then an enabled plugin without a client blocks instead of allowing tools.
    """
    return None
