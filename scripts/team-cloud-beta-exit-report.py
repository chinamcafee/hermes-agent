#!/usr/bin/env python3
"""Write the P4 Team Cloud beta exit report artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from team_cloud.beta_exit import build_beta_exit_report


DEFAULT_OUTPUT = Path("teamDoc/GADoc/artifacts/pilot/team-cloud-beta-exit-report-v0.json")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(build_beta_exit_report(), indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": "written", "output": str(output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
