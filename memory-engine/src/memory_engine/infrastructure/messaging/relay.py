"""The outbox relay: publishes pending handoffs and records the outcome (7.4 section 9.1).

One message per database transaction:

1. Claim the oldest due ``pending`` row (``FOR UPDATE SKIP LOCKED``).
2. Lock its subject (Memory Source or processing operation) and check it is
   still waiting for handoff (``validated`` / ``created``). If not, for example
   because a deletion cancelled the operation, the row becomes ``failed`` with
   ``SUBJECT_NOT_PENDING`` and nothing is published.
3. Publish and wait for the broker's confirmation.
4. Confirmed: mark the row ``published`` and move the subject to ``queued``
   (with a ``pm_source_processing_event`` for a Memory Source), then commit.
   Not confirmed: count the attempt, record the error code and schedule the
   next try with exponential backoff and jitter; after ``max_attempts`` the row
   becomes ``failed`` until an explicit retry. The subject is never moved.

If the commit after a confirmed publish fails, the row stays ``pending`` and is
published again later: delivery is at least once, and consumers deduplicate on
the message id (7.4 section 9.2).

The relay is a system process: it claims rows of every owner, then performs each
write under that row's owner scope.
"""

import logging
import secrets
import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from memory_engine.config.settings import OutboxSettings
from memory_engine.documents.domain.vocabulary import OperationStatus
from memory_engine.domain.handoff import HandoffKind, OutboxMessage
from memory_engine.domain.identifiers import OwnerScope, new_id
from memory_engine.domain.vocabulary import ProcessingEventType, SourceProcessingStatus
from memory_engine.exceptions import MessagePublishError, PersistenceError
from memory_engine.infrastructure.messaging.publisher import MessagePublisher
from memory_engine.infrastructure.persistence.database import translate_database_errors
from memory_engine.infrastructure.persistence.documents.models import ProcessingOperationRow
from memory_engine.infrastructure.persistence.documents.repositories import (
    SqlAlchemyProcessingOperationRepository,
)
from memory_engine.infrastructure.persistence.outbox import SqlAlchemyOutboxRepository
from memory_engine.infrastructure.persistence.personal.lifecycle_repositories import (
    SqlAlchemyProcessingHistoryRepository,
)
from memory_engine.infrastructure.persistence.personal.models import MemorySourceRow
from memory_engine.observability import get_logger
from memory_engine.personal.domain import SourceProcessingEvent

SUBJECT_NOT_PENDING = "SUBJECT_NOT_PENDING"

_logger = get_logger("outbox.relay")
_RANDOM = secrets.SystemRandom()


class RelayOutcome(StrEnum):
    PUBLISHED = "published"
    RETRY_SCHEDULED = "retry_scheduled"
    FAILED = "failed"  # attempts exhausted; waits for an explicit retry
    ABANDONED = "abandoned"  # the subject no longer waits for this handoff


@dataclass(slots=True)
class RelayReport:
    published: int = 0
    retry_scheduled: int = 0
    failed: int = 0
    abandoned: int = 0

    def add(self, outcome: RelayOutcome) -> None:
        name = outcome.value
        setattr(self, name, getattr(self, name) + 1)

    @property
    def handled(self) -> int:
        return self.published + self.retry_scheduled + self.failed + self.abandoned


def backoff_seconds(attempts: int, settings: OutboxSettings) -> float:
    """Delay before the next try after ``attempts`` failures, without jitter."""
    exponent = min(attempts - 1, 60)  # no float overflow for absurd attempt counts
    return float(min(settings.backoff_max_seconds, settings.backoff_base_seconds * 2**exponent))


def jittered(delay: float) -> float:
    """Between half and all of ``delay``, so failed relays do not retry in lockstep."""
    return delay * _RANDOM.uniform(0.5, 1.0)


class _Subject(Protocol):
    def is_pending(self, session: Session, scope: OwnerScope, subject_id: uuid.UUID) -> bool: ...

    def mark_queued(
        self, session: Session, scope: OwnerScope, subject_id: uuid.UUID, at: datetime
    ) -> None: ...


class _MemorySourceSubject:
    def is_pending(self, session: Session, scope: OwnerScope, subject_id: uuid.UUID) -> bool:
        with translate_database_errors("lock memory source for handoff"):
            status = session.scalar(
                select(MemorySourceRow.processing_status)
                .where(MemorySourceRow.id == subject_id, MemorySourceRow.owner_id == scope.owner_id)
                .with_for_update()
            )
        return status == SourceProcessingStatus.VALIDATED.value

    def mark_queued(
        self, session: Session, scope: OwnerScope, subject_id: uuid.UUID, at: datetime
    ) -> None:
        SqlAlchemyProcessingHistoryRepository(session).transition(
            scope,
            SourceProcessingEvent(
                id=new_id(),
                owner_id=scope.owner_id,
                source_id=subject_id,
                event_type=ProcessingEventType.TRANSITION,
                from_status=SourceProcessingStatus.VALIDATED,
                to_status=SourceProcessingStatus.QUEUED,
                attempt=1,
                occurred_at=at,
            ),
        )


class _ProcessingOperationSubject:
    def is_pending(self, session: Session, scope: OwnerScope, subject_id: uuid.UUID) -> bool:
        with translate_database_errors("lock processing operation for handoff"):
            status = session.scalar(
                select(ProcessingOperationRow.status)
                .where(
                    ProcessingOperationRow.id == subject_id,
                    ProcessingOperationRow.owner_id == scope.owner_id,
                )
                .with_for_update()
            )
        return status == OperationStatus.CREATED.value

    def mark_queued(
        self, session: Session, scope: OwnerScope, subject_id: uuid.UUID, at: datetime
    ) -> None:
        SqlAlchemyProcessingOperationRepository(session).transition(
            scope, subject_id, OperationStatus.QUEUED, expected=OperationStatus.CREATED
        )


_SUBJECTS: dict[HandoffKind, _Subject] = {
    HandoffKind.PERSONAL_EXTRACTION: _MemorySourceSubject(),
    HandoffKind.DOCUMENT_EXTRACTION: _ProcessingOperationSubject(),
}


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class _Handled:
    message: OutboxMessage
    outcome: RelayOutcome
    error_code: str | None = None


class OutboxRelay:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        publisher: MessagePublisher,
        settings: OutboxSettings,
        *,
        clock: Callable[[], datetime] = _utc_now,
        jitter: Callable[[float], float] = jittered,
    ) -> None:
        self._session_factory = session_factory
        self._publisher = publisher
        self._settings = settings
        self._clock = clock
        self._jitter = jitter

    def relay_due(self, limit: int | None = None) -> RelayReport:
        """Handle up to ``limit`` due messages (default: the batch size).

        Stops early at the first publish failure. Raises :class:`PersistenceError`
        if the database fails; messages already handled stay handled, and the
        current one stays pending.
        """
        report = RelayReport()
        for _ in range(self._settings.batch_size if limit is None else limit):
            handled = self._relay_next()
            if handled is None:
                break
            report.add(handled.outcome)
            _log(handled)
            if handled.outcome in (RelayOutcome.RETRY_SCHEDULED, RelayOutcome.FAILED):
                # The broker refused one message; the rest would wait out the same
                # timeout. Stop this batch and let the backoff and poll interval act.
                break
        return report

    def run_forever(self, stop: threading.Event) -> None:
        """Relay until ``stop`` is set, pausing when nothing is due or the database fails."""
        while not stop.is_set():
            try:
                report = self.relay_due()
            except PersistenceError as err:
                _logger.warning(
                    "outbox relay could not reach the database",
                    extra={"event": "outbox.relay_error", "error_code": err.code},
                )
                report = RelayReport()
            if report.published < self._settings.batch_size:
                stop.wait(self._settings.poll_interval_seconds)

    def _relay_next(self) -> _Handled | None:
        session = self._session_factory()
        try:
            handled = self._handle_one(session)
            with translate_database_errors("commit outbox relay"):
                session.commit()
        except BaseException:
            session.rollback()
            raise
        finally:
            session.close()
        return handled

    def _handle_one(self, session: Session) -> _Handled | None:
        now = self._clock()
        outbox = SqlAlchemyOutboxRepository(session)
        message = outbox.claim_next(now)
        if message is None:
            return None
        scope = OwnerScope(message.owner_id)
        subject = _SUBJECTS[message.kind]
        if not subject.is_pending(session, scope, message.subject_id):
            outbox.record_failure(message, SUBJECT_NOT_PENDING, next_attempt_at=now, give_up=True)
            return _Handled(message, RelayOutcome.ABANDONED, SUBJECT_NOT_PENDING)
        try:
            self._publisher.publish(message)
        except MessagePublishError as err:
            attempts = message.attempts + 1
            give_up = attempts >= self._settings.max_attempts
            delay = self._jitter(backoff_seconds(attempts, self._settings))
            outbox.record_failure(
                message,
                err.code,
                next_attempt_at=now + timedelta(seconds=delay),
                give_up=give_up,
            )
            outcome = RelayOutcome.FAILED if give_up else RelayOutcome.RETRY_SCHEDULED
            return _Handled(message, outcome, err.code)
        outbox.mark_published(message, now)
        subject.mark_queued(session, scope, message.subject_id, now)
        return _Handled(message, RelayOutcome.PUBLISHED)


def _log(handled: _Handled) -> None:
    # Identifiers and codes only (7.7 section 18); never the envelope payload.
    level = logging.INFO if handled.outcome is RelayOutcome.PUBLISHED else logging.WARNING
    _logger.log(
        level,
        "outbox message %s",
        handled.outcome.value,
        extra={
            "event": f"outbox.{handled.outcome.value}",
            "message_id": str(handled.message.id),
            "handoff_kind": handled.message.kind.value,
            "subject_id": str(handled.message.subject_id),
            "attempts": handled.message.attempts + (0 if handled.error_code is None else 1),
            "error_code": handled.error_code,
        },
    )
