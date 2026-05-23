"""Worker application skeleton for Team Cloud."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import time
from typing import Any

from . import __version__
from .config import TeamCloudConfig, load_config


@dataclass(frozen=True)
class TeamCloudWorker:
    config: TeamCloudConfig
    queues: tuple[str, ...] = field(default_factory=tuple)
    casdoor_sync_worker: Any | None = None

    def heartbeat(self) -> dict[str, object]:
        return {
            "service": "team-cloud-worker",
            "status": "ok",
            "version": __version__,
            "queues": list(self.queues),
        }

    def run_casdoor_reconcile(self):
        if self.casdoor_sync_worker is None:
            raise RuntimeError("casdoor_sync_worker is not configured")
        return self.casdoor_sync_worker.reconcile()


def create_worker(config: TeamCloudConfig | None = None) -> TeamCloudWorker:
    return TeamCloudWorker(config or load_config())


def main() -> None:
    worker = create_worker()
    while True:
        print(json.dumps(worker.heartbeat(), sort_keys=True), flush=True)
        time.sleep(30)


if __name__ == "__main__":
    main()
