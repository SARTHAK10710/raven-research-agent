"""Reliable handoff of ingested work: the message contract and the outbox port.

Owner-approved in Phase 8.3 step 4 (7.1 section 24.3; 7.4 sections 7 and 9):

- Every handoff is a *command* carried in the 7.4 section 7 task envelope,
  ``schema_version`` "1". Additive changes keep the version; any other change
  bumps it, and consumers reject versions they do not know.
- The payload holds identifiers and object-key references only, never content
  (7.4 section 7: large objects are referenced, not copied).
- Ingestion writes an :class:`OutboxMessage` in the same transaction as the
  record it hands off. A relay publishes it later; only after the broker
  confirms is the record moved to ``queued``. Delivery is at least once, so a
  consumer must deduplicate on ``message_id`` / ``idempotency_key``.

This module is part of the shared kernel: it holds no broker, Celery or
database code.
"""

import re
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Protocol

from memory_engine.domain.errors import DomainValidationError
from memory_engine.domain.identifiers import OwnerScope, new_id

ENVELOPE_SCHEMA_VERSION = "1"
SOURCE_COMPONENT = "memory_engine.ingestion"
MESSAGE_TYPE_COMMAND = "command"

_SAFE_CODE = re.compile(r"[A-Z][A-Z0-9_]{0,63}")
_PAYLOAD_KEY = re.compile(r"[a-z][a-z0-9_]{0,63}")
MAX_PAYLOAD_VALUE = 512


class HandoffKind(StrEnum):
    """What a handoff asks for; one queue per kind (7.1 section 24.3)."""

    DOCUMENT_EXTRACTION = "document_extraction"  # document pipeline, plan 8.12
    PERSONAL_EXTRACTION = "personal_extraction"  # memory extraction, plan 8.4

    @property
    def destination(self) -> str:
        return _DESTINATIONS[self]


_DESTINATIONS = {
    HandoffKind.DOCUMENT_EXTRACTION: "memory_engine.document_pipeline",
    HandoffKind.PERSONAL_EXTRACTION: "memory_engine.extraction",
}


class OutboxStatus(StrEnum):
    """Publication state of an outbox message (owner-approved, 8.3 step 4).

    ``failed`` is terminal until an explicit retry; it never means the work failed,
    only that the message was not handed off.
    """

    PENDING = "pending"
    PUBLISHED = "published"
    FAILED = "failed"


def validate_code(value: str | None, name: str = "error_code") -> None:
    if value is not None and not _SAFE_CODE.fullmatch(value):
        raise DomainValidationError(f"{name} must be an UPPER_SNAKE_CASE code")


def _require_aware(name: str, value: datetime | None) -> None:
    if value is not None and value.utcoffset() is None:
        raise DomainValidationError(f"{name} must be timezone-aware")


def _opt_text(data: Mapping[str, Any], name: str) -> str | None:
    value = data.get(name)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise DomainValidationError(f"envelope field {name} is not a non-empty string")
    return value


def _text(data: Mapping[str, Any], name: str) -> str:
    value = _opt_text(data, name)
    if value is None:
        raise DomainValidationError(f"envelope field {name} is missing")
    return value


def _opt_uuid(data: Mapping[str, Any], name: str) -> uuid.UUID | None:
    value = _opt_text(data, name)
    if value is None:
        return None
    try:
        return uuid.UUID(value)
    except ValueError as err:
        raise DomainValidationError(f"envelope field {name} is not a UUID") from err


def _uuid(data: Mapping[str, Any], name: str) -> uuid.UUID:
    value = _opt_uuid(data, name)
    if value is None:
        raise DomainValidationError(f"envelope field {name} is missing")
    return value


@dataclass(frozen=True, slots=True, kw_only=True)
class HandoffEnvelope:
    """The standard task envelope (7.4 section 7), version 1.

    ``user_id`` is the owner of every record the payload names. ``payload``
    maps lowercase keys to short strings (identifiers, object keys, codes).
    """

    message_id: uuid.UUID
    task_id: uuid.UUID
    user_id: uuid.UUID
    operation: HandoffKind
    created_at: datetime
    correlation_id: uuid.UUID
    idempotency_key: str
    priority: str
    payload: Mapping[str, str]
    payload_reference: str | None = None
    execution_id: uuid.UUID | None = None
    causation_id: uuid.UUID | None = None
    trace_context: Mapping[str, str] = field(default_factory=dict)
    schema_version: str = ENVELOPE_SCHEMA_VERSION
    source_component: str = SOURCE_COMPONENT
    message_type: str = MESSAGE_TYPE_COMMAND

    def __post_init__(self) -> None:
        if self.schema_version != ENVELOPE_SCHEMA_VERSION:
            raise DomainValidationError("unsupported envelope schema_version")
        if self.message_type != MESSAGE_TYPE_COMMAND:
            raise DomainValidationError("handoff messages are commands")
        if self.created_at.utcoffset() is None:
            raise DomainValidationError("created_at must be timezone-aware")
        if not self.idempotency_key.strip() or len(self.idempotency_key) > 200:
            raise DomainValidationError("idempotency_key must be 1-200 characters")
        if self.priority not in ("normal", "high"):
            raise DomainValidationError("priority must be normal or high")
        if not self.source_component.strip():
            raise DomainValidationError("source_component is required")
        for key, value in self.payload.items():
            if not _PAYLOAD_KEY.fullmatch(key):
                raise DomainValidationError("payload keys are lowercase identifiers")
            if not isinstance(value, str) or len(value) > MAX_PAYLOAD_VALUE:
                raise DomainValidationError("payload values are short strings")
        object.__setattr__(self, "payload", MappingProxyType(dict(self.payload)))
        object.__setattr__(self, "trace_context", MappingProxyType(dict(self.trace_context)))

    @property
    def destination_component(self) -> str:
        return self.operation.destination

    def to_dict(self) -> dict[str, Any]:
        """JSON-compatible form; the wire format of version 1."""
        return {
            "schema_version": self.schema_version,
            "message_id": str(self.message_id),
            "execution_id": None if self.execution_id is None else str(self.execution_id),
            "task_id": str(self.task_id),
            "user_id": str(self.user_id),
            "source_component": self.source_component,
            "destination_component": self.destination_component,
            "message_type": self.message_type,
            "operation": self.operation.value,
            "created_at": self.created_at.isoformat(),
            "correlation_id": str(self.correlation_id),
            "causation_id": None if self.causation_id is None else str(self.causation_id),
            "payload_reference": self.payload_reference,
            "priority": self.priority,
            "idempotency_key": self.idempotency_key,
            "trace_context": dict(self.trace_context),
            "payload": dict(self.payload),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "HandoffEnvelope":
        """Validate a received envelope (7.4 section 7.1); raises ``DomainValidationError``.

        Unknown schema versions, operations and destinations are refused, so an
        invalid message is never processed as a valid business task.
        """
        if data.get("schema_version") != ENVELOPE_SCHEMA_VERSION:
            raise DomainValidationError("unsupported envelope schema_version")
        try:
            operation = HandoffKind(_text(data, "operation"))
        except ValueError as err:
            raise DomainValidationError("unknown envelope operation") from err
        if data.get("destination_component") != operation.destination:
            raise DomainValidationError("destination does not match the operation")
        try:
            created_at = datetime.fromisoformat(_text(data, "created_at"))
        except ValueError as err:
            raise DomainValidationError("created_at is not an ISO timestamp") from err
        payload = data.get("payload")
        trace = data.get("trace_context", {})
        if not isinstance(payload, Mapping) or not isinstance(trace, Mapping):
            raise DomainValidationError("payload and trace_context must be objects")
        return cls(
            schema_version=ENVELOPE_SCHEMA_VERSION,
            message_id=_uuid(data, "message_id"),
            execution_id=_opt_uuid(data, "execution_id"),
            task_id=_uuid(data, "task_id"),
            user_id=_uuid(data, "user_id"),
            source_component=_text(data, "source_component"),
            message_type=_text(data, "message_type"),
            operation=operation,
            created_at=created_at,
            correlation_id=_uuid(data, "correlation_id"),
            causation_id=_opt_uuid(data, "causation_id"),
            payload_reference=_opt_text(data, "payload_reference"),
            priority=_text(data, "priority"),
            idempotency_key=_text(data, "idempotency_key"),
            trace_context=dict(trace),
            payload=dict(payload),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class OutboxMessage:
    """One handoff waiting for, or past, publication (7.4 section 9.1).

    ``subject_id`` is the record the message hands off: a Memory Source for
    personal extraction, a processing operation for document extraction.
    """

    id: uuid.UUID
    owner_id: uuid.UUID
    kind: HandoffKind
    subject_id: uuid.UUID
    envelope: HandoffEnvelope
    status: OutboxStatus
    next_attempt_at: datetime
    attempts: int = 0
    last_error_code: str | None = None
    published_at: datetime | None = None

    def __post_init__(self) -> None:
        _require_aware("next_attempt_at", self.next_attempt_at)
        _require_aware("published_at", self.published_at)
        if self.attempts < 0:
            raise DomainValidationError("attempts must not be negative")
        validate_code(self.last_error_code, "last_error_code")
        if (self.status is OutboxStatus.PUBLISHED) != (self.published_at is not None):
            raise DomainValidationError("published_at is set exactly for published messages")
        envelope = self.envelope
        if envelope.message_id != self.id or envelope.user_id != self.owner_id:
            raise DomainValidationError("the envelope must name this message and its owner")
        if envelope.operation is not self.kind or envelope.task_id != self.subject_id:
            raise DomainValidationError("the envelope must describe this handoff")

    @classmethod
    def new(
        cls,
        scope: OwnerScope,
        *,
        kind: HandoffKind,
        subject_id: uuid.UUID,
        payload: Mapping[str, str],
        payload_reference: str | None,
        priority: str,
        created_at: datetime,
        correlation_id: uuid.UUID | None = None,
    ) -> "OutboxMessage":
        """A pending handoff of ``subject_id``; one per subject and kind."""
        message_id = new_id()
        envelope = HandoffEnvelope(
            message_id=message_id,
            task_id=subject_id,
            user_id=scope.owner_id,
            operation=kind,
            created_at=created_at,
            correlation_id=correlation_id or message_id,
            idempotency_key=f"{kind.value}:{subject_id}",
            priority=priority,
            payload=payload,
            payload_reference=payload_reference,
        )
        return cls(
            id=message_id,
            owner_id=scope.owner_id,
            kind=kind,
            subject_id=subject_id,
            envelope=envelope,
            status=OutboxStatus.PENDING,
            next_attempt_at=created_at,
        )


class OutboxWriter(Protocol):
    """Records a handoff in the caller's transaction (part of a unit of work)."""

    def add(self, scope: OwnerScope, message: OutboxMessage) -> None:
        """Refuses a message of another owner and a second handoff of the same subject."""
        ...

    def rearm(
        self, scope: OwnerScope, kind: HandoffKind, subject_id: uuid.UUID, now: datetime
    ) -> None:
        """Make a subject's published or failed handoff pending again (explicit reprocess).

        The same message is published again, so consumers see its id twice and
        rely on the subject's state, never on the message, to decide what to do.
        """
        ...
