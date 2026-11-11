"""Structured logging, correlation context, ingestion events and the metrics port.

OpenTelemetry instrumentation is deferred until monitoring is deployed (7.1
section 22.1; 7.7 section 20). Correlation identifiers flow through logs, and
metrics go through the :class:`Metrics` port (no-op by default; 8.3 step 5).
"""

from memory_engine.observability.context import (
    CORRELATION_FIELDS,
    current_log_context,
    log_context,
)
from memory_engine.observability.ingestion import IngestionObservation, observe_ingestion
from memory_engine.observability.logging import (
    LOGGER_NAMESPACE,
    REDACTED,
    JsonFormatter,
    configure_logging,
    get_logger,
    is_sensitive_key,
)
from memory_engine.observability.metrics import (
    NO_METRICS,
    InMemoryMetrics,
    Metrics,
    NoOpMetrics,
    validate_labels,
)

__all__ = [
    "CORRELATION_FIELDS",
    "LOGGER_NAMESPACE",
    "NO_METRICS",
    "REDACTED",
    "InMemoryMetrics",
    "IngestionObservation",
    "JsonFormatter",
    "Metrics",
    "NoOpMetrics",
    "configure_logging",
    "current_log_context",
    "get_logger",
    "is_sensitive_key",
    "log_context",
    "observe_ingestion",
    "validate_labels",
]
