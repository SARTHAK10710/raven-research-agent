"""Correlation identifiers carried into every log record.

Identifiers follow Phase 7.7 section 5. The Orchestrator owns execution and
task identity; the Memory Engine only carries the identifiers it is given.
"""

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from types import MappingProxyType

CORRELATION_FIELDS: tuple[str, ...] = (
    "request_id",
    "execution_id",
    "task_id",
    "message_id",
    "correlation_id",
    "causation_id",
    "trace_id",
    "span_id",
)

_EMPTY: Mapping[str, str] = MappingProxyType({})
_log_context: ContextVar[Mapping[str, str]] = ContextVar("raven_memory_log_context", default=_EMPTY)


def current_log_context() -> Mapping[str, str]:
    """Return the correlation identifiers active in the current context."""
    return _log_context.get()


@contextmanager
def log_context(**identifiers: str) -> Iterator[None]:
    """Attach correlation identifiers to log records emitted inside the block.

    Nested blocks add to (and may override) outer identifiers; the previous
    values are restored on exit, including after an exception.

    Raises:
        ValueError: If an identifier name is not a known correlation field.
    """
    unknown = sorted(set(identifiers) - set(CORRELATION_FIELDS))
    if unknown:
        raise ValueError(f"Unknown correlation fields: {', '.join(unknown)}")
    token = _log_context.set(MappingProxyType({**_log_context.get(), **identifiers}))
    try:
        yield
    finally:
        _log_context.reset(token)
