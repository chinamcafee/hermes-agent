#!/usr/bin/env python3
"""Import or dry-run local Hermes SessionDB history."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from team_cloud.cloud_sessions import InMemoryCloudSessionRepository
from team_cloud.sessiondb_import import import_sessiondb


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, help="Path to Hermes state.db")
    parser.add_argument("--org-id", required=True)
    parser.add_argument("--team-id", required=True)
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--identity-map", required=True, help="JSON local user_id to member_id map")
    parser.add_argument("--default-member-id")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    report = import_sessiondb(
        args.db,
        InMemoryCloudSessionRepository(),
        org_id=args.org_id,
        team_id=args.team_id,
        project_id=args.project_id,
        identity_map=_load_identity_map(Path(args.identity_map)),
        default_member_id=args.default_member_id,
        dry_run=args.dry_run,
    )
    print(json.dumps(report, indent=2, sort_keys=False))


def _load_identity_map(path: Path) -> dict[str, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit("--identity-map must point to a JSON object")
    return {str(key): str(value) for key, value in data.items()}


if __name__ == "__main__":
    main()
