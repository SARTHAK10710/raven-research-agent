"""SQLAlchemy models for processing, evaluation, correction and deletion records (0005).

Phase 8.2 step 5. Integrity enforced by PostgreSQL in addition to owner-scoped
foreign keys:

* Processing events and candidate evaluations are append-only history ordered
  by ``seq``; each event changes the status, and an evaluation's outcome limits
  the candidate status it leaves.
* A ``deleted`` correction request holds no content (5.4.24 rule 7); a resolved
  one records when. Affected memories reference the exact revisions involved.
* Deletion operations are unique per owner and idempotency key and are finished
  exactly when ``finished_at`` is set. Ledger rows name records by kind and
  identifier only, with no foreign key, so they outlive purged records and can
  be replayed after a restore.
* Error and reason codes are UPPER_SNAKE_CASE codes, never free text.
"""

import uuid
from collections.abc import Iterable
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Double,
    ForeignKeyConstraint,
    Identity,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from memory_engine.domain.vocabulary import (
    CandidateStatus,
    CorrectionStatus,
    DeletionAction,
    DeletionOperationStatus,
    DeletionRequestKind,
    DeletionTargetKind,
    DeletionTargetState,
    EvaluationOutcome,
    ProcessingEventType,
    SourceProcessingStatus,
)
from memory_engine.infrastructure.persistence.base import Base, in_vocabulary
from memory_engine.infrastructure.persistence.personal.models import score_range

Json = dict[str, Any]


def _safe_code(column: str) -> str:
    return f"{column} IS NULL OR {column} ~ '^[A-Z][A-Z0-9_]{{0,63}}$'"


def _quoted(values: Iterable[str]) -> str:
    return ", ".join(f"'{value}'" for value in values)


OUTCOME_STATUSES = " OR ".join(
    f"(outcome = '{outcome.value}' AND to_status IN "
    f"({_quoted(sorted(s.value for s in outcome.allowed_statuses()))}))"
    for outcome in EvaluationOutcome
)
RESOLVED_CORRECTION = _quoted(s.value for s in CorrectionStatus if s.resolved)
FINISHED_DELETION = _quoted(s.value for s in DeletionOperationStatus if s.finished)


def _now() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


def _updated() -> Mapped[datetime]:
    return mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


def _owner_fk(column: str, table: str) -> ForeignKeyConstraint:
    return ForeignKeyConstraint(
        [column, "owner_id"], [f"{table}.id", f"{table}.owner_id"], ondelete="RESTRICT"
    )


# --- source processing and candidate evaluation ---------------------------------------


# 5.4 Phase 8.4 amendment: a reason code exactly for deferral and rejection.
REASON_REQUIRED = "(to_status IN ('deferred', 'rejected')) = (reason_code IS NOT NULL)"


class SourceProcessingEventRow(Base):
    __tablename__ = "pm_source_processing_event"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    seq: Mapped[int] = mapped_column(BigInteger, Identity(always=True), nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    event_type: Mapped[str] = mapped_column(String(16), nullable=False)
    from_status: Mapped[str] = mapped_column(String(32), nullable=False)
    to_status: Mapped[str] = mapped_column(String(32), nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64))
    reason_code: Mapped[str | None] = mapped_column(String(64))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = _now()

    __table_args__ = (
        _owner_fk("source_id", "pm_memory_source"),
        in_vocabulary("event_type", ProcessingEventType, name="event_type"),
        in_vocabulary("from_status", SourceProcessingStatus, name="from_status"),
        in_vocabulary("to_status", SourceProcessingStatus, name="to_status"),
        CheckConstraint("from_status <> to_status", name="status_changes"),
        CheckConstraint("attempt >= 1", name="attempt_positive"),
        CheckConstraint("(event_type = 'failure') = (error_code IS NOT NULL)", name="failure_code"),
        CheckConstraint(_safe_code("error_code"), name="error_code"),
        CheckConstraint(REASON_REQUIRED, name="reason_required"),
        CheckConstraint(_safe_code("reason_code"), name="reason_code"),
        Index(None, "owner_id", "source_id"),
    )


class CandidateEvaluationRow(Base):
    __tablename__ = "pm_candidate_evaluation"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    seq: Mapped[int] = mapped_column(BigInteger, Identity(always=True), nullable=False)
    candidate_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    from_status: Mapped[str] = mapped_column(String(32), nullable=False)
    to_status: Mapped[str] = mapped_column(String(32), nullable=False)
    importance: Mapped[float | None] = mapped_column(Double)
    confidence: Mapped[float | None] = mapped_column(Double)
    reason_code: Mapped[str | None] = mapped_column(String(64))
    method: Mapped[str] = mapped_column(Text, nullable=False)
    method_version: Mapped[str] = mapped_column(Text, nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = _now()

    __table_args__ = (
        _owner_fk("candidate_id", "pm_memory_candidate"),
        in_vocabulary("outcome", EvaluationOutcome, name="outcome"),
        in_vocabulary("from_status", CandidateStatus, name="from_status"),
        in_vocabulary("to_status", CandidateStatus, name="to_status"),
        CheckConstraint(OUTCOME_STATUSES, name="outcome_status"),
        *score_range(("importance", "confidence")),
        CheckConstraint(_safe_code("reason_code"), name="reason_code"),
        CheckConstraint("length(btrim(method)) > 0", name="method"),
        Index(None, "owner_id", "candidate_id"),
    )


# --- corrections -----------------------------------------------------------------------


class CorrectionRequestRow(Base):
    __tablename__ = "pm_correction_request"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    proposed_change: Mapped[Json | None] = mapped_column(JSONB)
    evidence: Mapped[Json] = mapped_column(JSONB, nullable=False, server_default="{}")
    resolution_note: Mapped[str | None] = mapped_column(Text)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = _now()
    updated_at: Mapped[datetime] = _updated()

    __table_args__ = (
        UniqueConstraint("id", "owner_id"),
        in_vocabulary("status", CorrectionStatus, name="status"),
        CheckConstraint(
            "(status = 'deleted') = (proposed_change IS NULL)", name="content_until_deleted"
        ),
        CheckConstraint(
            "status <> 'deleted' OR (evidence = '{}'::jsonb AND resolution_note IS NULL)",
            name="deleted_keeps_no_content",
        ),
        CheckConstraint(
            "status <> 'open' OR (resolved_at IS NULL AND resolution_note IS NULL)",
            name="open_unresolved",
        ),
        CheckConstraint(
            f"status NOT IN ({RESOLVED_CORRECTION}) OR resolved_at IS NOT NULL",
            name="resolved_has_time",
        ),
        CheckConstraint(
            "resolved_at IS NULL OR resolved_at >= requested_at", name="resolved_after_requested"
        ),
        CheckConstraint(
            "resolution_note IS NULL OR length(btrim(resolution_note)) > 0",
            name="resolution_note",
        ),
        Index(None, "owner_id", "status"),
    )


class CorrectionMemoryRow(Base):
    __tablename__ = "pm_correction_memory"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    request_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    memory_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    base_revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    applied_revision_number: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = _now()
    updated_at: Mapped[datetime] = _updated()

    __table_args__ = (
        UniqueConstraint("request_id", "memory_id"),
        _owner_fk("request_id", "pm_correction_request"),
        _owner_fk("memory_id", "pm_atomic_memory"),
        # Explicit names: both keys start with memory_id, so the convention would collide.
        ForeignKeyConstraint(
            ["memory_id", "base_revision_number"],
            ["pm_atomic_memory_revision.memory_id", "pm_atomic_memory_revision.revision_number"],
            ondelete="RESTRICT",
            name="fk_pm_correction_memory_base_revision",
        ),
        ForeignKeyConstraint(
            ["memory_id", "applied_revision_number"],
            ["pm_atomic_memory_revision.memory_id", "pm_atomic_memory_revision.revision_number"],
            ondelete="RESTRICT",
            name="fk_pm_correction_memory_applied_revision",
        ),
        CheckConstraint("base_revision_number >= 1", name="base_revision_positive"),
        CheckConstraint(
            "applied_revision_number IS NULL OR applied_revision_number > base_revision_number",
            name="applied_after_base",
        ),
        Index(None, "owner_id", "memory_id"),
    )


# --- deletion ------------------------------------------------------------------------


class DeletionOperationRow(Base):
    __tablename__ = "pm_deletion_operation"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    request_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = _now()
    updated_at: Mapped[datetime] = _updated()

    __table_args__ = (
        UniqueConstraint("id", "owner_id"),
        UniqueConstraint("owner_id", "idempotency_key"),
        in_vocabulary("request_kind", DeletionRequestKind, name="request_kind"),
        in_vocabulary("status", DeletionOperationStatus, name="status"),
        CheckConstraint(
            f"(status IN ({FINISHED_DELETION})) = (finished_at IS NOT NULL)",
            name="finished_has_time",
        ),
        CheckConstraint(
            "finished_at IS NULL OR finished_at >= requested_at", name="finished_after_requested"
        ),
        CheckConstraint("status <> 'failed' OR error_code IS NOT NULL", name="failure_code"),
        CheckConstraint("status <> 'completed' OR error_code IS NULL", name="completed_clean"),
        CheckConstraint(_safe_code("error_code"), name="error_code"),
        CheckConstraint("length(btrim(idempotency_key)) > 0", name="idempotency_key"),
        Index(None, "owner_id", "status"),
    )


class DeletionTargetRow(Base):
    __tablename__ = "pm_deletion_target"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    operation_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    target_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    direct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = _now()
    updated_at: Mapped[datetime] = _updated()

    __table_args__ = (
        UniqueConstraint("operation_id", "target_kind", "target_id"),
        _owner_fk("operation_id", "pm_deletion_operation"),
        in_vocabulary("target_kind", DeletionTargetKind, name="target_kind"),
        in_vocabulary("action", DeletionAction, name="action"),
        in_vocabulary("state", DeletionTargetState, name="state"),
        CheckConstraint("attempts >= 0", name="attempts"),
        CheckConstraint("(state = 'failed') = (error_code IS NOT NULL)", name="failure_code"),
        CheckConstraint(_safe_code("error_code"), name="error_code"),
        Index(None, "owner_id", "target_kind", "target_id"),
    )
