#!/usr/bin/env python3
"""Write the P2 memory performance baseline artifact."""

from __future__ import annotations

import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from team_cloud.memory.performance import build_memory_performance_baseline


OUTPUT_PATH = Path("teamDoc/GADoc/artifacts/memory-performance-baseline-v0.json")


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(build_memory_performance_baseline(), indent=2, sort_keys=False)
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
