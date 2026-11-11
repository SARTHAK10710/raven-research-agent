"""The extraction worker's application service (plan 8.4; owner-approved, 8.4 step 1).

It consumes ``personal_extraction`` handoffs (7.1 section 24.3) and runs one
Memory Source through the extraction pipeline. The pipeline itself (relevance
gate, fact extraction, evaluation, candidates; 6.2.2-6.2.6) arrives in steps
2-5 behind the :class:`ExtractionPipeline` port.

**Atomic outcome** (owner decision): the pipeline runs in memory; then one
transaction writes the candidates and moves the source ``queued`` ->
``processing`` -> outcome (two events), conditional on ``queued``. A crash
leaves nothing partial; a second delivery of the same message finds the
source no longer ``queued`` and does nothing.

- Envelopes are validated first (7.4 section 7.1); an invalid message is
  refused, never processed.
- Forget instructions never reach extraction (plan 8.3 section 5.4); a
  forget source that arrives anyway is left untouched for plan 8.10.
- Non-English sources are ``deferred`` with ``UNSUPPORTED_LANGUAGE`` (G6).
- Unreadable normalized content ends ``parsing_failed``; a pipeline failure
  ends ``processing_failed``, each with an error code.
- Transient infrastructure failures (database, object storage) propagate, so
  the Celery task retries them; when retries run out, :meth:`mark_failed`
  moves the source to ``processing_failed``. :meth:`reprocess_failed` is the
  explicit way back: ``processing_failed`` -> ``validated`` and the same
  handoff re-armed.
"""

import json
import logging
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Protocol

from memory_engine.domain.errors import DomainValidationError
from memory_engine.domain.handoff import HandoffEnvelope, HandoffKind
from memory_engine.domain.identifiers import OwnerScope, new_id
from memory_engine.domain.object_storage import ObjectStorage
from memory_engine.domain.vocabulary import (
    InstructionType,
    ProcessingEventType,
    SourceProcessingStatus,
)
from memory_engine.exceptions import (
    ConcurrencyConflictError,
    MemoryEngineError,
    ObjectStorageError,
    PersistenceError,
)
from memory_engine.observability import get_logger
from memory_engine.personal.application.language import LanguagePolicy, assess
from memory_engine.personal.application.ports import PersonalUnitOfWorkFactory
from memory_engine.personal.domain import MemoryCandidate, MemorySource, SourceProcessingEvent

NORMALIZATION_VERSION = "1"
MALFORMED_CONTENT = "MALFORMED_NORMALIZED_CONTENT"
EXTRACTION_FAILED = "EXTRACTION_FAILED"
# Errors that a later attempt may not hit: the Celery task retries these.
TRANSIENT_ERRORS: tuple[type[Exception], ...] = (PersistenceError, ObjectStorageError)

_logger = get_logger("extraction")

_PIPELINE_STATUSES = frozenset(
    {
        SourceProcessingStatus.EXTRACTED,
        SourceProcessingStatus.PARTIALLY_EXTRACTED,
        SourceProcessingStatus.REJECTED,
        SourceProcessingStatus.DEFERRED,
    }
)
_FAILURE_STATUSES = frozenset(
    {SourceProcessingStatus.PARSING_FAILED, SourceProcessingStatus.PROCESSING_FAILED}
)


@dataclass(frozen=True, slots=True, kw_only=True)
class Segment:
    """One normalized unit of a source: the text, or one conversation message."""

    position: int
    text: str
    from_user: bool = True
    speaker: str | None = None
    sent_at: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class SourceContent:
    source: MemorySource
    segments: Sequence[Segment]


@dataclass(frozen=True, slots=True, kw_only=True)
class PipelineResult:
    """What the pipeline concluded about one source; persisted atomically."""

    status: SourceProcessingStatus
    candidates: Sequence[MemoryCandidate] = ()
    reason_code: str | None = None

    def __post_init__(self) -> None:
        if self.status not in _PIPELINE_STATUSES:
            raise DomainValidationError("a pipeline ends extracted, partial, rejected or deferred")
        if self.status.needs_reason != (self.reason_code is not None):
            raise DomainValidationError("deferral and rejection need a reason code")
        if self.candidates and self.status not in (
            SourceProcessingStatus.EXTRACTED,
            SourceProcessingStatus.PARTIALLY_EXTRACTED,
        ):
            raise DomainValidationError("only an extracted source produces candidates")


class ExtractionPipeline(Protocol):
    def run(self, content: SourceContent) -> PipelineResult: ...


class ExtractionOutcome(StrEnum):
    COMPLETED = "completed"  # the source reached a final state now
    ALREADY_HANDLED = "already_handled"  # duplicate or late delivery: nothing done
    INVALID_MESSAGE = "invalid_message"
    SOURCE_MISSING = "source_missing"
    FORGET_REFUSED = "forget_refused"


_UNUSUAL = frozenset(
    {
        ExtractionOutcome.INVALID_MESSAGE,
        ExtractionOutcome.SOURCE_MISSING,
        ExtractionOutcome.FORGET_REFUSED,
    }
)


@dataclass(frozen=True, slots=True, kw_only=True)
class ExtractionReport:
    outcome: ExtractionOutcome
    source_id: uuid.UUID | None = None
    status: SourceProcessingStatus | None = None
    candidates: int = 0
    reason_code: str | None = None
    error_code: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "outcome": self.outcome.value,
            "source_id": None if self.source_id is None else str(self.source_id),
            "status": None if self.status is None else self.status.value,
            "candidates": self.candidates,
            "reason_code": self.reason_code,
            "error_code": self.error_code,
        }


@dataclass(frozen=True, slots=True)
class _Outcome:
    status: SourceProcessingStatus
    candidates: Sequence[MemoryCandidate] = field(default=())
    reason_code: str | None = None
    error_code: str | None = None


def parse_segments(data: bytes) -> list[Segment]:
    """Read the normalized representation written by ingestion (plan 8.3 step 2)."""
    try:
        document = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as err:
        raise DomainValidationError("normalized content is not JSON") from err
    if not isinstance(document, dict) or (
        document.get("normalization_version") != NORMALIZATION_VERSION
    ):
        raise DomainValidationError("unsupported normalized content")
    if isinstance(document.get("text"), str):
        return [Segment(position=0, text=document["text"])]
    messages = document.get("messages")
    if not isinstance(messages, list) or not messages:
        raise DomainValidationError("normalized content has no text or messages")
    segments: list[Segment] = []
    for message in messages:
        if not isinstance(message, dict) or not isinstance(message.get("text"), str):
            raise DomainValidationError("malformed normalized message")
        segments.append(
            Segment(
                position=int(message.get("position", len(segments))),
                text=message["text"],
                from_user=bool(message.get("from_user", False)),
                speaker=message.get("speaker"),
                sent_at=message.get("sent_at"),
            )
        )
    return segments


def _utc_now() -> datetime:
    return datetime.now(UTC)


class ExtractionService:
    def __init__(
        self,
        uow_factory: PersonalUnitOfWorkFactory,
        storage: ObjectStorage,
        pipeline: ExtractionPipeline,
        language: LanguagePolicy,
        *,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._uow_factory = uow_factory
        self._storage = storage
        self._pipeline = pipeline
        self._language = language
        self._clock = clock

    def handle(self, message: Mapping[str, Any], *, attempt: int = 1) -> ExtractionReport:
        """Process one handoff. Transient infrastructure errors propagate (retry)."""
        envelope = _envelope(message)
        if envelope is None:
            return _report(ExtractionReport(outcome=ExtractionOutcome.INVALID_MESSAGE))
        scope = OwnerScope(envelope.user_id)
        source_id = envelope.task_id
        with self._uow_factory() as uow:
            source = uow.sources.get(scope, source_id)
        if source is None:
            return _report(ExtractionReport(outcome=ExtractionOutcome.SOURCE_MISSING), scope)
        if source.instruction_type is InstructionType.FORGET:
            return _report(_refused(source), scope)
        if source.processing_status is not SourceProcessingStatus.QUEUED:
            return _report(_already(source), scope)
        return self._complete(scope, source, self._run(scope, source), attempt)

    def mark_failed(
        self, message: Mapping[str, Any], error_code: str, *, attempt: int
    ) -> ExtractionReport:
        """Retries ran out: ``queued`` -> ``processing_failed`` (visible, reprocessable)."""
        envelope = _envelope(message)
        if envelope is None:
            return _report(ExtractionReport(outcome=ExtractionOutcome.INVALID_MESSAGE))
        scope = OwnerScope(envelope.user_id)
        try:
            with self._uow_factory() as uow:
                uow.processing.transition(
                    scope,
                    self._event(
                        scope,
                        envelope.task_id,
                        SourceProcessingStatus.QUEUED,
                        SourceProcessingStatus.PROCESSING_FAILED,
                        attempt,
                        error_code=error_code,
                    ),
                )
        except ConcurrencyConflictError:
            return _report(
                ExtractionReport(
                    outcome=ExtractionOutcome.ALREADY_HANDLED, source_id=envelope.task_id
                ),
                scope,
            )
        return _report(
            ExtractionReport(
                outcome=ExtractionOutcome.COMPLETED,
                source_id=envelope.task_id,
                status=SourceProcessingStatus.PROCESSING_FAILED,
                error_code=error_code,
            ),
            scope,
        )

    def reprocess_failed(self, scope: OwnerScope, source_id: uuid.UUID) -> None:
        """The explicit retry: ``processing_failed`` -> ``validated``, handoff re-armed.

        The outbox relay then publishes the same message again and queues the
        source, exactly as after registration.
        """
        now = self._clock()
        with self._uow_factory() as uow:
            failures = sum(
                1
                for e in uow.processing.events(scope, source_id)
                if e.event_type is ProcessingEventType.FAILURE
            )
            uow.processing.transition(
                scope,
                SourceProcessingEvent(
                    id=new_id(),
                    owner_id=scope.owner_id,
                    source_id=source_id,
                    event_type=ProcessingEventType.RETRY,
                    from_status=SourceProcessingStatus.PROCESSING_FAILED,
                    to_status=SourceProcessingStatus.VALIDATED,
                    attempt=failures + 1,
                    occurred_at=now,
                ),
            )
            uow.outbox.rearm(scope, HandoffKind.PERSONAL_EXTRACTION, source_id, now)

    def _run(self, scope: OwnerScope, source: MemorySource) -> _Outcome:
        if source.normalized_ref is None:
            return _Outcome(SourceProcessingStatus.PARSING_FAILED, error_code=MALFORMED_CONTENT)
        data = self._storage.get(scope, source.normalized_ref)  # transient errors propagate
        try:
            segments = parse_segments(data)
        except DomainValidationError:
            return _Outcome(SourceProcessingStatus.PARSING_FAILED, error_code=MALFORMED_CONTENT)
        language = assess((s.text for s in segments), self._language)
        if not language.english:
            return _Outcome(SourceProcessingStatus.DEFERRED, reason_code=language.reason_code)
        try:
            result = self._pipeline.run(SourceContent(source=source, segments=segments))
        except TRANSIENT_ERRORS:
            raise
        except Exception as err:
            code = err.code if isinstance(err, MemoryEngineError) else EXTRACTION_FAILED
            return _Outcome(SourceProcessingStatus.PROCESSING_FAILED, error_code=code)
        for candidate in result.candidates:
            if candidate.owner_id != scope.owner_id or candidate.source_id != source.id:
                return _Outcome(
                    SourceProcessingStatus.PROCESSING_FAILED, error_code="INVALID_CANDIDATE"
                )
        return _Outcome(result.status, result.candidates, reason_code=result.reason_code)

    def _complete(
        self, scope: OwnerScope, source: MemorySource, outcome: _Outcome, attempt: int
    ) -> ExtractionReport:
        try:
            with self._uow_factory() as uow:
                uow.processing.transition(
                    scope,
                    self._event(
                        scope,
                        source.id,
                        SourceProcessingStatus.QUEUED,
                        SourceProcessingStatus.PROCESSING,
                        attempt,
                    ),
                )
                for candidate in outcome.candidates:
                    uow.candidates.add(scope, candidate)
                uow.processing.transition(
                    scope,
                    self._event(
                        scope,
                        source.id,
                        SourceProcessingStatus.PROCESSING,
                        outcome.status,
                        attempt,
                        error_code=outcome.error_code,
                        reason_code=outcome.reason_code,
                    ),
                )
        except ConcurrencyConflictError:  # another delivery finished it first
            return _report(_already(source), scope)
        return _report(
            ExtractionReport(
                outcome=ExtractionOutcome.COMPLETED,
                source_id=source.id,
                status=outcome.status,
                candidates=len(outcome.candidates),
                reason_code=outcome.reason_code,
                error_code=outcome.error_code,
            ),
            scope,
        )

    def _event(
        self,
        scope: OwnerScope,
        source_id: uuid.UUID,
        from_status: SourceProcessingStatus,
        to_status: SourceProcessingStatus,
        attempt: int,
        *,
        error_code: str | None = None,
        reason_code: str | None = None,
    ) -> SourceProcessingEvent:
        return SourceProcessingEvent(
            id=new_id(),
            owner_id=scope.owner_id,
            source_id=source_id,
            event_type=(
                ProcessingEventType.FAILURE
                if to_status in _FAILURE_STATUSES
                else ProcessingEventType.TRANSITION
            ),
            from_status=from_status,
            to_status=to_status,
            attempt=attempt,
            occurred_at=self._clock(),
            error_code=error_code,
            reason_code=reason_code,
        )


def _envelope(message: Mapping[str, Any]) -> HandoffEnvelope | None:
    try:
        envelope = HandoffEnvelope.from_dict(message)
    except DomainValidationError:
        return None
    if envelope.operation is not HandoffKind.PERSONAL_EXTRACTION:
        return None
    return envelope


def _already(source: MemorySource) -> ExtractionReport:
    return ExtractionReport(
        outcome=ExtractionOutcome.ALREADY_HANDLED,
        source_id=source.id,
        status=source.processing_status,
    )


def _refused(source: MemorySource) -> ExtractionReport:
    return ExtractionReport(
        outcome=ExtractionOutcome.FORGET_REFUSED,
        source_id=source.id,
        status=source.processing_status,
    )


def _report(report: ExtractionReport, scope: OwnerScope | None = None) -> ExtractionReport:
    # Identifiers, states and codes only; never the content (7.7 section 18).
    if report.outcome is ExtractionOutcome.COMPLETED and report.status is not None:
        event_type = f"extraction.{report.status.value}"
    else:
        event_type = f"extraction.{report.outcome.value}"
    warn = report.status in _FAILURE_STATUSES or report.outcome in _UNUSUAL
    extra: dict[str, Any] = {
        "event_type": event_type,
        **{k: v for k, v in report.as_dict().items() if v is not None},
    }
    if scope is not None:
        extra["user_scope"] = str(scope.owner_id)
    _logger.log(
        logging.WARNING if warn else logging.INFO,
        "extraction %s",
        report.outcome.value,
        extra=extra,
    )
    return report
