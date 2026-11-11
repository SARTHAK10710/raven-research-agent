"""Metrics port for the Memory Engine (owner-approved, 8.3 step 5; 7.7 sections 4.2 and 7).

Application code records counters, durations and gauges through :class:`Metrics`.
7.7 selects OpenTelemetry and Prometheus, but no monitoring is deployed yet
(7.7 section 20; 7.8), so this package ships only a no-op recorder (the
default) and an in-memory recorder for tests. An OpenTelemetry adapter
implements the same port when monitoring is deployed; no dependency until then.

Labels are bounded (7.7 section 7.7): only the keys in :data:`LABEL_KEYS`, and
values that are short lowercase words or UPPER_SNAKE_CASE codes. Identifiers
such as owner ids can therefore never become labels; they belong in logs.
"""

import re
from collections import defaultdict
from collections.abc import Mapping
from types import MappingProxyType
from typing import Protocol

# --- metric names (Prometheus-style; plan 8.3 section 11, 7.7 sections 7.3 and 7.5) ---

INGESTION_REQUESTS = "memory_ingestion_requests_total"  # input, outcome
INGESTION_REJECTIONS = "memory_ingestion_rejections_total"  # input, reason
INGESTION_DURATION = "memory_ingestion_duration_seconds"  # input, outcome
DOCUMENT_REGISTRATIONS = "memory_document_registrations_total"  # kind
HANDOFF_ATTEMPTS = "memory_handoff_attempts_total"  # kind, outcome
HANDOFF_LATENCY = "memory_handoff_latency_seconds"  # kind: registration to confirmed publish
OUTBOX_PENDING = "memory_outbox_pending"  # gauge
OUTBOX_FAILED = "memory_outbox_failed"  # gauge
OUTBOX_OLDEST_PENDING_AGE = "memory_outbox_oldest_pending_age_seconds"  # gauge

LABEL_KEYS = frozenset({"input", "outcome", "reason", "kind"})
_LABEL_VALUE = re.compile(r"(?=.{1,64}$)(?:[a-z]+(?:_[a-z]+)*|[A-Z][A-Z0-9_]*)")

Labels = Mapping[str, str]
_LabelKey = tuple[tuple[str, str], ...]


def validate_labels(labels: Labels | None) -> _LabelKey:
    """Refuse unknown label keys and anything that is not a short word or code."""
    if not labels:
        return ()
    for key, value in labels.items():
        if key not in LABEL_KEYS:
            raise ValueError(f"unknown metric label {key!r}")
        if not isinstance(value, str) or not _LABEL_VALUE.fullmatch(value):
            raise ValueError(f"metric label {key!r} must be a short word or code")
    return tuple(sorted(labels.items()))


class Metrics(Protocol):
    def increment(self, name: str, labels: Labels | None = None, amount: int = 1) -> None: ...

    def observe(self, name: str, value: float, labels: Labels | None = None) -> None:
        """Record one measurement, such as a duration in seconds."""
        ...

    def set_gauge(self, name: str, value: float, labels: Labels | None = None) -> None: ...


class NoOpMetrics:
    """Validates labels and records nothing: the default until monitoring exists."""

    def increment(self, name: str, labels: Labels | None = None, amount: int = 1) -> None:
        validate_labels(labels)

    def observe(self, name: str, value: float, labels: Labels | None = None) -> None:
        validate_labels(labels)

    def set_gauge(self, name: str, value: float, labels: Labels | None = None) -> None:
        validate_labels(labels)


NO_METRICS = NoOpMetrics()


class InMemoryMetrics:
    """Keeps every value in memory, for tests."""

    def __init__(self) -> None:
        self._counters: dict[tuple[str, _LabelKey], int] = defaultdict(int)
        self._observations: dict[tuple[str, _LabelKey], list[float]] = defaultdict(list)
        self._gauges: dict[tuple[str, _LabelKey], float] = {}

    def increment(self, name: str, labels: Labels | None = None, amount: int = 1) -> None:
        if amount < 0:
            raise ValueError("counters only increase")
        self._counters[(name, validate_labels(labels))] += amount

    def observe(self, name: str, value: float, labels: Labels | None = None) -> None:
        self._observations[(name, validate_labels(labels))].append(value)

    def set_gauge(self, name: str, value: float, labels: Labels | None = None) -> None:
        self._gauges[(name, validate_labels(labels))] = value

    def count(self, name: str, **labels: str) -> int:
        return self._counters.get((name, validate_labels(labels)), 0)

    def observations(self, name: str, **labels: str) -> list[float]:
        return list(self._observations.get((name, validate_labels(labels)), []))

    def gauge(self, name: str, **labels: str) -> float | None:
        return self._gauges.get((name, validate_labels(labels)))

    def label_values(self) -> Mapping[str, frozenset[str]]:
        """Every label value recorded, by key (to check that no identifier leaked)."""
        values: dict[str, set[str]] = defaultdict(set)
        for store in (self._counters, self._observations, self._gauges):
            for _, key in store:
                for label, value in key:
                    values[label].add(value)
        return MappingProxyType({k: frozenset(v) for k, v in values.items()})
