"""Structured logging helpers for Team Cloud."""

from __future__ import annotations

import json
import logging as stdlib_logging
import sys
from pathlib import Path
from typing import Any, TextIO

from pydantic import SecretStr

_RESERVED_LOG_RECORD_KEYS = set(stdlib_logging.makeLogRecord({}).__dict__)


class JsonFormatter(stdlib_logging.Formatter):
    def format(self, record: stdlib_logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key in _RESERVED_LOG_RECORD_KEYS:
                continue
            payload[key] = _sanitize(value)
        payload.setdefault("event", record.getMessage())
        return json.dumps(payload, sort_keys=True)


def configure_logging(
    *,
    level: str | int = "INFO",
    stream: TextIO | None = None,
) -> stdlib_logging.Logger:
    handler = stdlib_logging.StreamHandler(stream or sys.stderr)
    handler.setFormatter(JsonFormatter())

    logger = stdlib_logging.getLogger("team_cloud")
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    return logger


def get_logger(name: str = "team_cloud") -> stdlib_logging.Logger:
    return stdlib_logging.getLogger(name)


def _sanitize(value: Any) -> Any:
    if isinstance(value, SecretStr):
        return "********"
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_sanitize(item) for item in value]
    return value
