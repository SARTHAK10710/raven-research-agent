"""The transactional outbox, ``me_outbox`` (7.1 sections 23.6 and 24.3; 7.4 section 9).

Ingestion adds a row in the same transaction as the record it hands off, through
the unit of work's ``outbox`` (owner-scoped like every repository). The relay
(``memory_engine.infrastructure.messaging``) then claims due rows across all
owners with ``FOR UPDATE SKIP LOCKED``, so several relays never publish the same
row at once; every write it makes afterwards is scoped to the row's owner.

There is deliberately no foreign key to the subject: it is a Memory Source or a
document processing operation, and only the evidence path may cross the two
domains' tables. Deleting a subject (plan 8.10) must therefore remove its
outbox rows explicitly.
"""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    func,
    select,
    text,
    update,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, Session, mapped_column

from memory_engine.domain.errors import OwnershipError
from memory_engine.domain.handoff import (
    HandoffEnvelope,
    HandoffKind,
    OutboxMessage,
    OutboxStatus,
    validate_code,
)
from memory_engine.domain.identifiers import OwnerScope
from memory_engine.infrastructure.persistence.base import Base, in_vocabulary
from memory_engine.infrastructure.persistence.database import (
    conditional_update,
    translate_database_errors,
)

PUBLISHED_AT_RULE = "(status = 'published') = (published_at IS NOT NULL)"
SAFE_LAST_ERROR = "last_error_code IS NULL OR last_error_code ~ '^[A-Z][A-Z0-9_]{0,63}$'"


class OutboxRow(Base):
    __tablename__ = "me_outbox"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    subject_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    envelope: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_error_code: Mapped[str | None] = mapped_column(String(64))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        # One handoff per subject and kind: a retried registration cannot queue twice.
        UniqueConstraint("owner_id", "kind", "subject_id"),
        in_vocabulary("kind", HandoffKind, name="kind"),
        in_vocabulary("status", OutboxStatus, name="status"),
        CheckConstraint("attempts >= 0", name="attempts"),
        CheckConstraint(PUBLISHED_AT_RULE, name="published_at"),
        CheckConstraint(SAFE_LAST_ERROR, name="last_error_code"),
        Index(
            "ix_me_outbox_due",
            "next_attempt_at",
            postgresql_where=text("status = 'pending'"),
        ),
    )


@dataclass(frozen=True, slots=True)
class OutboxBacklog:
    pending: int
    failed: int
    oldest_pending_age_seconds: float  # 0 when nothing is pending


def _message(row: OutboxRow) -> OutboxMessage:
    return OutboxMessage(
        id=row.id,
        owner_id=row.owner_id,
        kind=HandoffKind(row.kind),
        subject_id=row.subject_id,
        envelope=HandoffEnvelope.from_dict(row.envelope),
        status=OutboxStatus(row.status),
        next_attempt_at=row.next_attempt_at,
        attempts=row.attempts,
        last_error_code=row.last_error_code,
        published_at=row.published_at,
    )


class SqlAlchemyOutboxRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    # --- owner-scoped (units of work, operators, tests) -----------------------

    def add(self, scope: OwnerScope, message: OutboxMessage) -> None:
        if not scope.owns(message.owner_id):
            raise OwnershipError("outbox message belongs to a different owner scope")
        with translate_database_errors("add outbox message"):
            self._session.add(
                OutboxRow(
                    id=message.id,
                    owner_id=message.owner_id,
                    kind=message.kind.value,
                    subject_id=message.subject_id,
                    envelope=message.envelope.to_dict(),
                    status=message.status.value,
                    attempts=message.attempts,
                    next_attempt_at=message.next_attempt_at,
                    last_error_code=message.last_error_code,
                    published_at=message.published_at,
                )
            )
            self._session.flush()

    def get(self, scope: OwnerScope, message_id: uuid.UUID) -> OutboxMessage | None:
        with translate_database_errors("get outbox message"):
            row = self._session.scalar(
                select(OutboxRow).where(
                    OutboxRow.id == message_id, OutboxRow.owner_id == scope.owner_id
                )
            )
        return None if row is None else _message(row)

    def for_subject(self, scope: OwnerScope, subject_id: uuid.UUID) -> Sequence[OutboxMessage]:
        with translate_database_errors("list outbox messages"):
            rows = self._session.scalars(
                select(OutboxRow)
                .where(OutboxRow.owner_id == scope.owner_id, OutboxRow.subject_id == subject_id)
                .order_by(OutboxRow.created_at, OutboxRow.id)
            ).all()
        return [_message(row) for row in rows]

    def retry_failed(
        self,
        scope: OwnerScope,
        now: datetime,
        message_ids: Sequence[uuid.UUID] | None = None,
    ) -> int:
        """Make ``failed`` messages of this owner pending again (the explicit retry).

        Attempts restart at zero; the last error code stays for diagnosis.
        Returns the number of messages released.
        """
        statement = (
            update(OutboxRow)
            .where(
                OutboxRow.owner_id == scope.owner_id,
                OutboxRow.status == OutboxStatus.FAILED.value,
            )
            .values(status=OutboxStatus.PENDING.value, attempts=0, next_attempt_at=now)
        )
        if message_ids is not None:
            statement = statement.where(OutboxRow.id.in_(list(message_ids)))
        with translate_database_errors("retry failed outbox messages"):
            result = self._session.execute(statement)
        return int(result.rowcount)  # type: ignore[attr-defined]

    # --- relay (system process; claims across owners, then writes per owner) ---

    def backlog(self) -> OutboxBacklog:
        """Aggregate counts across owners, for metrics only (no identifiers leave here).

        The age uses the database clock on both sides, like ``created_at``.
        """
        with translate_database_errors("measure outbox backlog"):
            counts = dict(
                self._session.execute(
                    select(OutboxRow.status, func.count())
                    .where(OutboxRow.status != OutboxStatus.PUBLISHED.value)
                    .group_by(OutboxRow.status)
                ).all()
            )
            age = self._session.scalar(
                select(func.extract("epoch", func.now() - func.min(OutboxRow.created_at))).where(
                    OutboxRow.status == OutboxStatus.PENDING.value
                )
            )
        return OutboxBacklog(
            pending=int(counts.get(OutboxStatus.PENDING.value, 0)),
            failed=int(counts.get(OutboxStatus.FAILED.value, 0)),
            oldest_pending_age_seconds=0.0 if age is None else max(float(age), 0.0),
        )

    def claim_next(self, now: datetime) -> OutboxMessage | None:
        """Lock the oldest due pending message for this transaction, skipping locked ones."""
        with translate_database_errors("claim outbox message"):
            row = self._session.scalar(
                select(OutboxRow)
                .where(
                    OutboxRow.status == OutboxStatus.PENDING.value,
                    OutboxRow.next_attempt_at <= now,
                )
                .order_by(OutboxRow.next_attempt_at, OutboxRow.created_at, OutboxRow.id)
                .limit(1)
                .with_for_update(skip_locked=True)
            )
        return None if row is None else _message(row)

    def mark_published(self, message: OutboxMessage, at: datetime) -> None:
        self._transition(
            message,
            "mark outbox message published",
            status=OutboxStatus.PUBLISHED.value,
            published_at=at,
        )

    def record_failure(
        self,
        message: OutboxMessage,
        error_code: str,
        *,
        next_attempt_at: datetime,
        give_up: bool,
    ) -> None:
        """Count a failed attempt; ``give_up`` makes the message ``failed`` (no more retries)."""
        validate_code(error_code)
        self._transition(
            message,
            "record outbox failure",
            status=(OutboxStatus.FAILED if give_up else OutboxStatus.PENDING).value,
            attempts=OutboxRow.attempts + 1,
            last_error_code=error_code,
            next_attempt_at=next_attempt_at,
        )

    def _transition(self, message: OutboxMessage, operation: str, **values: Any) -> None:
        with translate_database_errors(operation):
            conditional_update(
                self._session,
                update(OutboxRow)
                .where(
                    OutboxRow.id == message.id,
                    OutboxRow.owner_id == message.owner_id,
                    OutboxRow.status == OutboxStatus.PENDING.value,
                )
                .values(**values),
                exists=select(OutboxRow.id)
                .where(OutboxRow.id == message.id, OutboxRow.owner_id == message.owner_id)
                .exists(),
                what="outbox message",
            )
