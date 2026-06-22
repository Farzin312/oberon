"""Structured JSON logging — switchable to console format via OBERON_LOG_FORMAT env var.

Uses stdlib logging with a JSON formatter (no external deps).
Set OBERON_LOG_FORMAT=console for human-readable output during development.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import UTC, datetime


class JSONFormatter(logging.Formatter):
    """One-line JSON log records for structured ingestion."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info and record.exc_info[1] is not None:
            payload["error"] = str(record.exc_info[1])
        # Attach extra fields (anything not in the standard LogRecord attrs).
        std = set(dir(logging.LogRecord("", 0, "", 0, "", (), None)))
        for key, value in record.__dict__.items():
            if key not in std and key not in ("message", "asctime"):
                payload[key] = value
        return json.dumps(payload, default=str)


class ConsoleFormatter(logging.Formatter):
    """Human-readable for terminal use: [LEVEL] logger: message extras."""

    def format(self, record: logging.LogRecord) -> str:
        std = set(dir(logging.LogRecord("", 0, "", 0, "", (), None)))
        extras = {k: v for k, v in record.__dict__.items() if k not in std and k not in ("message", "asctime")}
        base = f"[{record.levelname}] {record.name}: {record.getMessage()}"
        if extras:
            base += f" {json.dumps(extras, default=str)}"
        return base


def configure_logging(level: str = "INFO") -> None:
    """Configure root logger with JSON or console format based on env var."""
    fmt = os.environ.get("OBERON_LOG_FORMAT", "json")
    handler = logging.StreamHandler(sys.stderr)
    if fmt == "console":
        handler.setFormatter(ConsoleFormatter())
    else:
        handler.setFormatter(JSONFormatter())
    logging.root.handlers.clear()
    logging.root.addHandler(handler)
    logging.root.setLevel(level)


def get_logger(name: str) -> logging.Logger:
    """Get a structured logger. Call configure_logging() once at startup."""
    return logging.getLogger(name)
