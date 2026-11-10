"""Structured logging and correlation context.

OpenTelemetry instrumentation is deferred until it is implemented
(Phase 7.1 section 22.1); correlation identifiers already flow through logs.
"""

from memory_engine.observability.context import (
    CORRELATION_FIELDS,
    current_log_context,
    log_context,
)
from memory_engine.observability.logging import (
    LOGGER_NAMESPACE,
    REDACTED,
    JsonFormatter,
    configure_logging,
    get_logger,
    is_sensitive_key,
)

__all__ = [
    "CORRELATION_FIELDS",
    "LOGGER_NAMESPACE",
    "REDACTED",
    "JsonFormatter",
    "configure_logging",
    "current_log_context",
    "get_logger",
    "is_sensitive_key",
    "log_context",
]
