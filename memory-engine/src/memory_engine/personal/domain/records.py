"""Core Personal Memory records (Phase 5.4; Phase 8.2 amendment).

Records are immutable value objects. A change to a mutable record (for example
an Atomic Memory's current state) is expressed as a new instance with an
incremented revision, produced by the application layer and persisted with
optimistic concurrency.

Invariants checked here are the ones that need no database: ranges, required
fields, temporal ordering and timezone-awareness. Ownership consistency between
related records is enforced by repositories and by composite foreign keys.
"""

import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType
from typing import Any

from memory_engine.domain.errors import DomainValidationError
from memory_engine.domain.vocabulary import (
    CandidateOrigin,
    CandidateStatus,
    DocumentEvidenceStatus,
    MemoryLifecycleStatus,
    MemoryOrigin,
    ProvenanceOriginKind,
    ProvenanceRole,
    RevisionChangeType,
    SourceProcessingStatus,
    SourceType,
)

JsonMap = Mapping[str, Any]


def _empty() -> JsonMap:
    return MappingProxyType({})


def _require_aware(name: str, value: datetime | None) -> None:
    if value is not None and value.utcoffset() is None:
        raise DomainValidationError(f"{name} must be timezone-aware")


def _require_score(name: str, value: float | None) -> None:
    # Scores are normalized to [0, 1] (6.2.4); scales beyond that are not defined.
    if value is not None and not 0.0 <= value <= 1.0:
        raise DomainValidationError(f"{name} must be between 0 and 1")


def _require_text(name: str, value: str) -> None:
    if not value.strip():
        raise DomainValidationError(f"{name} must not be empty")


def _require_valid_interval(valid_from: datetime | None, valid_to: datetime | None) -> None:
    _require_aware("valid_from", valid_from)
    _require_aware("valid_to", valid_to)
    if valid_from is not None and valid_to is not None and valid_to < valid_from:
        raise DomainValidationError("valid_to must not be earlier than valid_from")


def _require_content_matches_lifecycle(
    content: str | None,
    status: MemoryLifecycleStatus,
    structured: JsonMap,
    context: JsonMap,
) -> None:
    if status is MemoryLifecycleStatus.DELETED:
        if content is not None or structured or context:
            raise DomainValidationError("a deleted memory keeps only a minimal tombstone")
    elif content is None:
        raise DomainValidationError("content is required unless the memory is deleted")
    else:
        _require_text("content", content)


def _frozen(value: JsonMap) -> JsonMap:
    return MappingProxyType(dict(value))


@dataclass(frozen=True, slots=True, kw_only=True)
class MemorySource:
    """An original input (Decision 5.4.1). Content lives in content storage.

    ``content_ref`` is the stable reference to stored content. It is optional
    until content storage exists (Phase 8.3); ``content_sha256`` lets
    reprocessing verify that the referenced content is unchanged.
    """

    id: uuid.UUID
    owner_id: uuid.UUID
    source_type: SourceType
    processing_status: SourceProcessingStatus
    received_at: datetime
    content_ref: str | None = None
    content_sha256: str | None = None

    def __post_init__(self) -> None:
        _require_aware("received_at", self.received_at)
        if self.content_ref is not None:
            _require_text("content_ref", self.content_ref)
        if self.content_sha256 is not None and (
            len(self.content_sha256) != 64
            or any(char not in "0123456789abcdef" for char in self.content_sha256)
        ):
            raise DomainValidationError("content_sha256 must be 64 lowercase hex characters")


@dataclass(frozen=True, slots=True, kw_only=True)
class MemoryCandidate:
    """An extracted proposition awaiting resolution (Decisions 5.4.2-5.4.3; 6.2.6).

    Importance, confidence and extraction confidence stay independent
    (6.2.6 rule 7).
    """

    id: uuid.UUID
    owner_id: uuid.UUID
    source_id: uuid.UUID
    proposition: str
    status: CandidateStatus
    origin: CandidateOrigin
    importance: float | None = None
    confidence: float | None = None
    extraction_confidence: float | None = None
    context: JsonMap = field(default_factory=_empty)
    temporal: JsonMap = field(default_factory=_empty)
    extraction_metadata: JsonMap = field(default_factory=_empty)

    def __post_init__(self) -> None:
        _require_text("proposition", self.proposition)
        _require_score("importance", self.importance)
        _require_score("confidence", self.confidence)
        _require_score("extraction_confidence", self.extraction_confidence)
        if self.origin is CandidateOrigin.UNRESOLVED and self.status is CandidateStatus.VALIDATED:
            # 6.2.6 rule 2: unresolved origin must remain in review.
            raise DomainValidationError("a candidate with unresolved origin cannot be validated")
        object.__setattr__(self, "context", _frozen(self.context))
        object.__setattr__(self, "temporal", _frozen(self.temporal))
        object.__setattr__(self, "extraction_metadata", _frozen(self.extraction_metadata))


@dataclass(frozen=True, slots=True, kw_only=True)
class AtomicMemory:
    """The current accepted state of one memory (Decisions 5.4.4-5.4.7).

    ``revision_number`` names the immutable revision that this state equals.
    Bitemporal fields follow the Phase 8.2 amendment section 8.
    """

    id: uuid.UUID
    owner_id: uuid.UUID
    content: str | None
    origin: MemoryOrigin
    lifecycle_status: MemoryLifecycleStatus
    recorded_at: datetime
    revision_number: int
    structured: JsonMap = field(default_factory=_empty)
    context: JsonMap = field(default_factory=_empty)
    importance: float | None = None
    confidence: float | None = None
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    observed_at: datetime | None = None
    superseded_at: datetime | None = None

    def __post_init__(self) -> None:
        _require_content_matches_lifecycle(
            self.content, self.lifecycle_status, self.structured, self.context
        )
        if self.revision_number < 1:
            raise DomainValidationError("revision_number starts at 1")
        _require_score("importance", self.importance)
        _require_score("confidence", self.confidence)
        _require_valid_interval(self.valid_from, self.valid_to)
        for name in ("recorded_at", "observed_at", "superseded_at"):
            _require_aware(name, getattr(self, name))
        if self.superseded_at is not None and self.superseded_at < self.recorded_at:
            raise DomainValidationError("superseded_at must not be earlier than recorded_at")
        object.__setattr__(self, "structured", _frozen(self.structured))
        object.__setattr__(self, "context", _frozen(self.context))


@dataclass(frozen=True, slots=True, kw_only=True)
class AtomicMemoryRevision:
    """An immutable snapshot of an Atomic Memory after one accepted change."""

    id: uuid.UUID
    owner_id: uuid.UUID
    memory_id: uuid.UUID
    revision_number: int
    change_type: RevisionChangeType
    content: str | None
    origin: MemoryOrigin
    lifecycle_status: MemoryLifecycleStatus
    recorded_at: datetime
    structured: JsonMap = field(default_factory=_empty)
    context: JsonMap = field(default_factory=_empty)
    importance: float | None = None
    confidence: float | None = None
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    observed_at: datetime | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        _require_content_matches_lifecycle(
            self.content, self.lifecycle_status, self.structured, self.context
        )
        if self.revision_number < 1:
            raise DomainValidationError("revision_number starts at 1")
        if (self.revision_number == 1) != (self.change_type is RevisionChangeType.CREATED):
            raise DomainValidationError("only the first revision has change type 'created'")
        _require_score("importance", self.importance)
        _require_score("confidence", self.confidence)
        _require_valid_interval(self.valid_from, self.valid_to)
        _require_aware("recorded_at", self.recorded_at)
        _require_aware("observed_at", self.observed_at)
        object.__setattr__(self, "structured", _frozen(self.structured))
        object.__setattr__(self, "context", _frozen(self.context))

    @classmethod
    def snapshot(
        cls,
        memory: AtomicMemory,
        *,
        revision_id: uuid.UUID,
        change_type: RevisionChangeType,
        reason: str | None = None,
    ) -> "AtomicMemoryRevision":
        """Capture ``memory`` exactly as it stands at its current revision number."""
        return cls(
            id=revision_id,
            owner_id=memory.owner_id,
            memory_id=memory.id,
            revision_number=memory.revision_number,
            change_type=change_type,
            content=memory.content,
            origin=memory.origin,
            lifecycle_status=memory.lifecycle_status,
            recorded_at=memory.recorded_at,
            structured=memory.structured,
            context=memory.context,
            importance=memory.importance,
            confidence=memory.confidence,
            valid_from=memory.valid_from,
            valid_to=memory.valid_to,
            observed_at=memory.observed_at,
            reason=reason,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class DocumentEvidenceRef:
    """A document passage that supports a document-derived Memory Candidate.

    Document facts reach Personal Memory only through
    ``Document Evidence -> Memory Candidate -> Evaluation -> Resolution``
    (5.4 Document Intelligence amendment section 5), so every reference belongs
    to a candidate. The identifiers are opaque here: this domain never imports
    Document Intelligence. After the document is deleted the status becomes
    ``source_deleted`` and the identifiers remain only as provenance.
    """

    id: uuid.UUID
    owner_id: uuid.UUID
    candidate_id: uuid.UUID
    document_ref: uuid.UUID
    version_ref: uuid.UUID
    extraction_method: str
    status: DocumentEvidenceStatus
    recorded_at: datetime
    chunk_ref: uuid.UUID | None = None
    page_number: int | None = None
    section_heading: str | None = None
    start_offset: int | None = None
    end_offset: int | None = None

    def __post_init__(self) -> None:
        _require_text("extraction_method", self.extraction_method)
        _require_aware("recorded_at", self.recorded_at)
        if self.page_number is not None and self.page_number < 1:
            raise DomainValidationError("page_number starts at 1")
        if self.start_offset is not None and self.start_offset < 0:
            raise DomainValidationError("start_offset must not be negative")
        if self.end_offset is not None and (
            self.start_offset is None or self.end_offset < self.start_offset
        ):
            raise DomainValidationError("end_offset requires a start_offset and must follow it")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProvenanceRecord:
    """Evidence linking a memory to a source, candidate or document passage (5.4.18).

    A record must name at least one piece of evidence.
    """

    id: uuid.UUID
    owner_id: uuid.UUID
    memory_id: uuid.UUID
    role: ProvenanceRole
    origin_kind: ProvenanceOriginKind
    recorded_at: datetime
    source_id: uuid.UUID | None = None
    candidate_id: uuid.UUID | None = None
    document_evidence_id: uuid.UUID | None = None
    revision_number: int | None = None

    def __post_init__(self) -> None:
        if (
            self.source_id is None
            and self.candidate_id is None
            and (self.document_evidence_id is None)
        ):
            raise DomainValidationError(
                "provenance must reference a source, a candidate or document evidence"
            )
        if self.revision_number is not None and self.revision_number < 1:
            raise DomainValidationError("revision_number starts at 1")
        _require_aware("recorded_at", self.recorded_at)
