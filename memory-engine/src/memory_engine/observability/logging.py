"""Structured JSON logging for the Memory Engine.

Uses the Python standard library only (Phase 7.7 section 3). Records carry the
conceptual fields from Phase 7.7 section 6.1: timestamp, level, service,
environment, component, message, correlation identifiers, and any structured
``extra`` fields such as ``event_type``, ``operation`` or ``duration_ms``.

Privacy rules applied here:

* ``extra`` fields whose names look sensitive (password, token, secret, ...)
  are replaced with ``[REDACTED]``.
* For exceptions, only the exception type and the Memory Engine error code are
  logged, never the exception message or traceback, because lower layers may
  put user data into messages (Raven engineering convention).
* Callers must not put raw personal-memory or document content into log
  messages.

``configure_logging`` configures only the ``raven.memory_engine`` logger. It
never touches the root logger, which belongs to the process entry point.
"""

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any, TextIO

from memory_engine.config.settings import MemoryEngineSettings
from memory_engine.exceptions.base import MemoryEngineError
from memory_engine.observability.context import current_log_context

LOGGER_NAMESPACE = "raven.memory_engine"
REDACTED = "[REDACTED]"

_SENSITIVE_KEY_PARTS: tuple[str, ...] = (
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "authorization",
    "credential",
    "private_key",
    "cookie",
    "session",
    "dsn",
)

# Attributes present on every LogRecord; anything else came from ``extra``.
_RECORD_ATTRIBUTES: frozenset[str] = frozenset(
    vars(logging.LogRecord("", logging.INFO, "", 0, "", None, None))
) | {"message", "asctime"}


def is_sensitive_key(key: str) -> bool:
    """Return True if a field name suggests it holds a secret."""
    lowered = key.lower()
    return any(part in lowered for part in _SENSITIVE_KEY_PARTS)


class JsonFormatter(logging.Formatter):
    """Render each record as one JSON object per line."""

    def __init__(self, *, service: str, environment: str) -> None:
        super().__init__()
        self._service = service
        self._environment = environment

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {}
        for key, value in record.__dict__.items():
            if key in _RECORD_ATTRIBUTES or key.startswith("_"):
                continue
            payload[key] = REDACTED if is_sensitive_key(key) else value
        payload.update(current_log_context())
        payload.update(
            {
                "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(
                    timespec="milliseconds"
                ),
                "level": record.levelname,
                "service": self._service,
                "environment": self._environment,
                "component": record.name,
                "message": record.getMessage(),
            }
        )
        if record.exc_info is not None and record.exc_info[1] is not None:
            error = record.exc_info[1]
            payload["error_type"] = type(error).__name__
            if isinstance(error, MemoryEngineError):
                payload["error_code"] = error.code
        return json.dumps(payload, default=str, ensure_ascii=False)


class _MemoryEngineHandler(logging.StreamHandler[TextIO]):
    """Marker type so repeated configuration replaces only our own handler."""


def configure_logging(
    settings: MemoryEngineSettings, *, stream: TextIO | None = None
) -> logging.Logger:
    """Configure the ``raven.memory_engine`` logger and return it.

    Safe to call more than once: an earlier Memory Engine handler is replaced,
    never duplicated. Records do not propagate to the root logger.
    """
    logger = logging.getLogger(LOGGER_NAMESPACE)
    for handler in list(logger.handlers):
        if isinstance(handler, _MemoryEngineHandler):
            logger.removeHandler(handler)
    handler = _MemoryEngineHandler(stream if stream is not None else sys.stderr)
    handler.setFormatter(
        JsonFormatter(service=settings.app_name, environment=settings.environment.value)
    )
    logger.addHandler(handler)
    logger.setLevel(settings.log_level)
    logger.propagate = False
    return logger


def get_logger(component: str) -> logging.Logger:
    """Return a logger for a Memory Engine component, e.g. ``"ingestion"``."""
    if not component or component.startswith(".") or component.endswith("."):
        raise ValueError("component must be a non-empty dotted name")
    return logging.getLogger(f"{LOGGER_NAMESPACE}.{component}")
