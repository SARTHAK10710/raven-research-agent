"""SQLAlchemy implementations of the processing, evaluation, correction and deletion ports.

Same contract as the other Personal Memory repositories: owner-scoped SQL,
scope checks before writes, domain records out, conditional updates for state
changes. A state change and its history record are written together, so the
current state never disagrees with the history (5.4.25, 5.4.28).
"""

import uuid
from collections.abc import Mapping, Sequence
from datetime import datetime

from sqlalchemy import Exists, exists, func, null, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from memory_engine.domain.errors import DomainValidationError, OwnershipError
from memory_engine.domain.identifiers import OwnerScope
from memory_engine.domain.vocabulary import (
    CandidateStatus,
    CorrectionStatus,
    DeletionAction,
    DeletionOperationStatus,
    DeletionRequestKind,
    DeletionTargetKind,
    DeletionTargetState,
    EvaluationOutcome,
    MemoryLifecycleStatus,
    ProcessingEventType,
    SourceProcessingStatus,
)
from memory_engine.exceptions import RecordNotFoundError
from memory_engine.infrastructure.persistence.database import (
    conditional_update,
    translate_database_errors,
)
from memory_engine.infrastructure.persistence.personal.lifecycle_models import (
    CandidateEvaluationRow,
    CorrectionMemoryRow,
    CorrectionRequestRow,
    DeletionOperationRow,
    DeletionTargetRow,
    SourceProcessingEventRow,
)
from memory_engine.infrastructure.persistence.personal.models import (
    AtomicMemoryRevisionRow,
    AtomicMemoryRow,
    MemoryCandidateRow,
    MemorySourceRow,
)
from memory_engine.personal.domain import (
    CandidateEvaluation,
    CorrectionRequest,
    CorrectionTarget,
    DeletionOperation,
    DeletionTarget,
    SourceProcessingEvent,
)

_TOMBSTONED_MEMORY = (
    MemoryLifecycleStatus.DELETION_PENDING.value,
    MemoryLifecycleStatus.DELETED.value,
)


def _require_in_scope(scope: OwnerScope, *owner_ids: uuid.UUID) -> None:
    if not all(scope.owns(owner_id) for owner_id in owner_ids):
        raise OwnershipError("record owner does not match the operation's owner scope")


def _require_aware(value: datetime) -> None:
    if value.utcoffset() is None:
        raise DomainValidationError("timestamps must be timezone-aware")


def _revision_exists(
    session: Session, scope: OwnerScope, memory_id: uuid.UUID, revision_number: int
) -> bool:
    return bool(
        session.scalar(
            select(
                exists().where(
                    AtomicMemoryRevisionRow.memory_id == memory_id,
                    AtomicMemoryRevisionRow.owner_id == scope.owner_id,
                    AtomicMemoryRevisionRow.revision_number == revision_number,
                )
            )
        )
    )


# --- mapping -----------------------------------------------------------------------


def _event(row: SourceProcessingEventRow) -> SourceProcessingEvent:
    return SourceProcessingEvent(
        id=row.id,
        owner_id=row.owner_id,
        source_id=row.source_id,
        event_type=ProcessingEventType(row.event_type),
        from_status=SourceProcessingStatus(row.from_status),
        to_status=SourceProcessingStatus(row.to_status),
        attempt=row.attempt,
        occurred_at=row.occurred_at,
        error_code=row.error_code,
    )


def _evaluation(row: CandidateEvaluationRow) -> CandidateEvaluation:
    return CandidateEvaluation(
        id=row.id,
        owner_id=row.owner_id,
        candidate_id=row.candidate_id,
        outcome=EvaluationOutcome(row.outcome),
        from_status=CandidateStatus(row.from_status),
        to_status=CandidateStatus(row.to_status),
        method=row.method,
        method_version=row.method_version,
        evaluated_at=row.evaluated_at,
        importance=row.importance,
        confidence=row.confidence,
        reason_code=row.reason_code,
    )


def _correction(row: CorrectionRequestRow) -> CorrectionRequest:
    return CorrectionRequest(
        id=row.id,
        owner_id=row.owner_id,
        status=CorrectionStatus(row.status),
        requested_at=row.requested_at,
        proposed_change=row.proposed_change,
        evidence=row.evidence,
        resolution_note=row.resolution_note,
        resolved_at=row.resolved_at,
    )


def _correction_target(row: CorrectionMemoryRow) -> CorrectionTarget:
    return CorrectionTarget(
        memory_id=row.memory_id,
        base_revision_number=row.base_revision_number,
        applied_revision_number=row.applied_revision_number,
    )


def _operation(row: DeletionOperationRow) -> DeletionOperation:
    return DeletionOperation(
        id=row.id,
        owner_id=row.owner_id,
        request_kind=DeletionRequestKind(row.request_kind),
        status=DeletionOperationStatus(row.status),
        idempotency_key=row.idempotency_key,
        requested_at=row.requested_at,
        finished_at=row.finished_at,
        error_code=row.error_code,
    )


def _target(row: DeletionTargetRow) -> DeletionTarget:
    return DeletionTarget(
        target_kind=DeletionTargetKind(row.target_kind),
        target_id=row.target_id,
        action=DeletionAction(row.action),
        direct=row.direct,
        state=DeletionTargetState(row.state),
        attempts=row.attempts,
        error_code=row.error_code,
    )


# --- source processing ---------------------------------------------------------------


class SqlAlchemyProcessingHistoryRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def transition(self, scope: OwnerScope, event: SourceProcessingEvent) -> None:
        _require_in_scope(scope, event.owner_id)
        with translate_database_errors("record source processing event"):
            conditional_update(
                self._session,
                update(MemorySourceRow)
                .where(
                    MemorySourceRow.id == event.source_id,
                    MemorySourceRow.owner_id == scope.owner_id,
                    MemorySourceRow.processing_status == event.from_status.value,
                )
                .values(processing_status=event.to_status.value),
                exists=select(MemorySourceRow.id)
                .where(
                    MemorySourceRow.id == event.source_id,
                    MemorySourceRow.owner_id == scope.owner_id,
                )
                .exists(),
                what="memory source",
            )
            self._session.add(
                SourceProcessingEventRow(
                    id=event.id,
                    owner_id=event.owner_id,
                    source_id=event.source_id,
                    event_type=event.event_type.value,
                    from_status=event.from_status.value,
                    to_status=event.to_status.value,
                    attempt=event.attempt,
                    error_code=event.error_code,
                    occurred_at=event.occurred_at,
                )
            )
            self._session.flush()

    def events(self, scope: OwnerScope, source_id: uuid.UUID) -> Sequence[SourceProcessingEvent]:
        with translate_database_errors("list source processing events"):
            rows = self._session.scalars(
                select(SourceProcessingEventRow)
                .where(
                    SourceProcessingEventRow.owner_id == scope.owner_id,
                    SourceProcessingEventRow.source_id == source_id,
                )
                .order_by(SourceProcessingEventRow.occurred_at, SourceProcessingEventRow.seq)
            ).all()
        return [_event(row) for row in rows]


# --- candidate evaluation ------------------------------------------------------------


class SqlAlchemyEvaluationHistoryRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def record(self, scope: OwnerScope, evaluation: CandidateEvaluation) -> None:
        _require_in_scope(scope, evaluation.owner_id)
        values: dict[str, object] = {"status": evaluation.to_status.value}
        if evaluation.importance is not None:
            values["importance"] = evaluation.importance
        if evaluation.confidence is not None:
            values["confidence"] = evaluation.confidence
        with translate_database_errors("record candidate evaluation"):
            conditional_update(
                self._session,
                update(MemoryCandidateRow)
                .where(
                    MemoryCandidateRow.id == evaluation.candidate_id,
                    MemoryCandidateRow.owner_id == scope.owner_id,
                    MemoryCandidateRow.status == evaluation.from_status.value,
                )
                .values(**values),
                exists=select(MemoryCandidateRow.id)
                .where(
                    MemoryCandidateRow.id == evaluation.candidate_id,
                    MemoryCandidateRow.owner_id == scope.owner_id,
                )
                .exists(),
                what="memory candidate",
            )
            self._session.add(
                CandidateEvaluationRow(
                    id=evaluation.id,
                    owner_id=evaluation.owner_id,
                    candidate_id=evaluation.candidate_id,
                    outcome=evaluation.outcome.value,
                    from_status=evaluation.from_status.value,
                    to_status=evaluation.to_status.value,
                    importance=evaluation.importance,
                    confidence=evaluation.confidence,
                    reason_code=evaluation.reason_code,
                    method=evaluation.method,
                    method_version=evaluation.method_version,
                    evaluated_at=evaluation.evaluated_at,
                )
            )
            self._session.flush()

    def history(self, scope: OwnerScope, candidate_id: uuid.UUID) -> Sequence[CandidateEvaluation]:
        with translate_database_errors("list candidate evaluations"):
            rows = self._session.scalars(
                select(CandidateEvaluationRow)
                .where(
                    CandidateEvaluationRow.owner_id == scope.owner_id,
                    CandidateEvaluationRow.candidate_id == candidate_id,
                )
                .order_by(CandidateEvaluationRow.evaluated_at, CandidateEvaluationRow.seq)
            ).all()
        return [_evaluation(row) for row in rows]


# --- corrections -----------------------------------------------------------------------


class SqlAlchemyCorrectionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def open(
        self, scope: OwnerScope, request: CorrectionRequest, targets: Sequence[CorrectionTarget]
    ) -> None:
        _require_in_scope(scope, request.owner_id)
        if request.status is not CorrectionStatus.OPEN:
            raise DomainValidationError("a new correction request is open")
        if not targets:
            raise DomainValidationError("a correction request affects at least one memory")
        if len({t.memory_id for t in targets}) != len(targets):
            raise DomainValidationError("each affected memory is listed once")
        if any(t.applied_revision_number is not None for t in targets):
            raise DomainValidationError("an open correction has not been applied")
        with translate_database_errors("open correction request"):
            for target in targets:
                self._require_live_revision(scope, target.memory_id, target.base_revision_number)
            self._session.add(
                CorrectionRequestRow(
                    id=request.id,
                    owner_id=request.owner_id,
                    status=request.status.value,
                    proposed_change=dict(request.proposed_change or {}),
                    evidence=dict(request.evidence),
                    requested_at=request.requested_at,
                )
            )
            self._session.flush()
            for target in targets:
                self._session.add(
                    CorrectionMemoryRow(
                        id=uuid.uuid4(),
                        owner_id=request.owner_id,
                        request_id=request.id,
                        memory_id=target.memory_id,
                        base_revision_number=target.base_revision_number,
                    )
                )
            self._session.flush()

    def get(self, scope: OwnerScope, request_id: uuid.UUID) -> CorrectionRequest | None:
        with translate_database_errors("get correction request"):
            row = self._session.scalar(
                select(CorrectionRequestRow)
                .where(
                    CorrectionRequestRow.id == request_id,
                    CorrectionRequestRow.owner_id == scope.owner_id,
                    CorrectionRequestRow.status != CorrectionStatus.DELETED.value,
                )
                .execution_options(populate_existing=True)
            )
        return None if row is None else _correction(row)

    def targets(self, scope: OwnerScope, request_id: uuid.UUID) -> Sequence[CorrectionTarget]:
        with translate_database_errors("list correction targets"):
            rows = self._session.scalars(
                select(CorrectionMemoryRow)
                .where(
                    CorrectionMemoryRow.owner_id == scope.owner_id,
                    CorrectionMemoryRow.request_id == request_id,
                )
                .order_by(CorrectionMemoryRow.memory_id)
                .execution_options(populate_existing=True)
            ).all()
        return [_correction_target(row) for row in rows]

    def resolve(
        self,
        scope: OwnerScope,
        request_id: uuid.UUID,
        status: CorrectionStatus,
        *,
        resolved_at: datetime,
        note: str | None = None,
        applied: Mapping[uuid.UUID, int] | None = None,
    ) -> CorrectionRequest:
        if not status.resolved:
            raise DomainValidationError(f"'{status}' does not resolve a correction request")
        _require_aware(resolved_at)
        applied = dict(applied or {})
        if (status is CorrectionStatus.ACCEPTED) != bool(applied):
            raise DomainValidationError(
                "only an accepted correction names the revisions that applied it"
            )
        with translate_database_errors("resolve correction request"):
            if self.get(scope, request_id) is None:
                raise RecordNotFoundError("correction request not found")
            # Check everything before writing anything.
            if status is CorrectionStatus.ACCEPTED:
                self._check_applied(scope, request_id, applied)
            conditional_update(
                self._session,
                update(CorrectionRequestRow)
                .where(
                    CorrectionRequestRow.id == request_id,
                    CorrectionRequestRow.owner_id == scope.owner_id,
                    CorrectionRequestRow.status == CorrectionStatus.OPEN.value,
                )
                .values(status=status.value, resolved_at=resolved_at, resolution_note=note),
                exists=_correction_exists(scope, request_id),
                what="correction request",
            )
            for memory_id, revision_number in applied.items():
                self._session.execute(
                    update(CorrectionMemoryRow)
                    .where(
                        CorrectionMemoryRow.owner_id == scope.owner_id,
                        CorrectionMemoryRow.request_id == request_id,
                        CorrectionMemoryRow.memory_id == memory_id,
                    )
                    .values(applied_revision_number=revision_number)
                    .execution_options(synchronize_session=False)
                )
        resolved = self.get(scope, request_id)
        if resolved is None:  # pragma: no cover - updated in this transaction
            raise RecordNotFoundError("correction request not found")
        return resolved

    def open_for_memory(
        self, scope: OwnerScope, memory_id: uuid.UUID
    ) -> Sequence[CorrectionRequest]:
        with translate_database_errors("list open corrections of memory"):
            rows = self._session.scalars(
                select(CorrectionRequestRow)
                .join(
                    CorrectionMemoryRow,
                    (CorrectionMemoryRow.request_id == CorrectionRequestRow.id)
                    & (CorrectionMemoryRow.owner_id == CorrectionRequestRow.owner_id),
                )
                .where(
                    CorrectionRequestRow.owner_id == scope.owner_id,
                    CorrectionRequestRow.status == CorrectionStatus.OPEN.value,
                    CorrectionMemoryRow.memory_id == memory_id,
                )
                .order_by(CorrectionRequestRow.requested_at, CorrectionRequestRow.id)
            ).all()
        return [_correction(row) for row in rows]

    def purge(self, scope: OwnerScope, request_id: uuid.UUID) -> None:
        with translate_database_errors("purge correction request"):
            result = self._session.execute(
                update(CorrectionRequestRow)
                .where(
                    CorrectionRequestRow.id == request_id,
                    CorrectionRequestRow.owner_id == scope.owner_id,
                    CorrectionRequestRow.status != CorrectionStatus.DELETED.value,
                )
                .values(
                    status=CorrectionStatus.DELETED.value,
                    # null(), not None: None is stored as the JSON value 'null'.
                    proposed_change=null(),
                    evidence={},
                    resolution_note=None,
                )
                .execution_options(synchronize_session=False)
            )
            if getattr(result, "rowcount", 0) == 0 and not self._session.scalar(
                select(_correction_exists(scope, request_id))
            ):
                raise RecordNotFoundError("correction request not found")

    def _check_applied(
        self, scope: OwnerScope, request_id: uuid.UUID, applied: Mapping[uuid.UUID, int]
    ) -> None:
        targets = {t.memory_id: t for t in self.targets(scope, request_id)}
        if set(applied) != set(targets):
            raise DomainValidationError(
                "an accepted correction names an applied revision for every affected memory"
            )
        for memory_id, revision_number in applied.items():
            if revision_number <= targets[memory_id].base_revision_number:
                raise DomainValidationError("a correction is applied by a later revision")
            if not _revision_exists(self._session, scope, memory_id, revision_number):
                raise RecordNotFoundError("atomic memory revision not found")

    def _require_live_revision(
        self, scope: OwnerScope, memory_id: uuid.UUID, revision_number: int
    ) -> None:
        live = self._session.scalar(
            select(
                exists().where(
                    AtomicMemoryRow.id == memory_id,
                    AtomicMemoryRow.owner_id == scope.owner_id,
                    AtomicMemoryRow.lifecycle_status.not_in(_TOMBSTONED_MEMORY),
                )
            )
        )
        if not live or not _revision_exists(self._session, scope, memory_id, revision_number):
            raise RecordNotFoundError("atomic memory revision not found")


def _correction_exists(scope: OwnerScope, request_id: uuid.UUID) -> Exists:
    return (
        select(CorrectionRequestRow.id)
        .where(
            CorrectionRequestRow.id == request_id,
            CorrectionRequestRow.owner_id == scope.owner_id,
        )
        .exists()
    )


# --- deletion ------------------------------------------------------------------------


class SqlAlchemyDeletionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        scope: OwnerScope,
        operation: DeletionOperation,
        targets: Sequence[DeletionTarget],
    ) -> tuple[DeletionOperation, bool]:
        _require_in_scope(scope, operation.owner_id)
        if operation.status is not DeletionOperationStatus.REQUESTED:
            raise DomainValidationError("a new deletion operation is requested")
        if not any(target.direct for target in targets):
            raise DomainValidationError("a deletion names at least one record directly")
        _require_new_targets(targets)
        with translate_database_errors("create deletion operation"):
            inserted = self._session.scalar(
                pg_insert(DeletionOperationRow)
                .values(
                    id=operation.id,
                    owner_id=operation.owner_id,
                    request_kind=operation.request_kind.value,
                    status=operation.status.value,
                    idempotency_key=operation.idempotency_key,
                    requested_at=operation.requested_at,
                )
                .on_conflict_do_nothing(index_elements=["owner_id", "idempotency_key"])
                .returning(DeletionOperationRow.id)
            )
            if inserted is not None:
                self._insert_targets(scope, operation.id, targets)
            row = self._session.scalar(
                select(DeletionOperationRow)
                .where(
                    DeletionOperationRow.owner_id == scope.owner_id,
                    DeletionOperationRow.idempotency_key == operation.idempotency_key,
                )
                .execution_options(populate_existing=True)
            )
        if row is None:  # pragma: no cover - the row was just inserted or already existed
            raise RecordNotFoundError("deletion operation not found")
        return _operation(row), inserted is not None

    def get(self, scope: OwnerScope, operation_id: uuid.UUID) -> DeletionOperation | None:
        with translate_database_errors("get deletion operation"):
            row = self._session.scalar(
                select(DeletionOperationRow)
                .where(
                    DeletionOperationRow.id == operation_id,
                    DeletionOperationRow.owner_id == scope.owner_id,
                )
                .execution_options(populate_existing=True)
            )
        return None if row is None else _operation(row)

    def add_targets(
        self, scope: OwnerScope, operation_id: uuid.UUID, targets: Sequence[DeletionTarget]
    ) -> int:
        _require_new_targets(targets)
        with translate_database_errors("add deletion targets"):
            operation = self.get(scope, operation_id)
            if operation is None:
                raise RecordNotFoundError("deletion operation not found")
            if operation.status.finished:
                raise DomainValidationError("a finished deletion operation takes no new targets")
            return self._insert_targets(scope, operation_id, targets)

    def targets(
        self,
        scope: OwnerScope,
        operation_id: uuid.UUID,
        *,
        state: DeletionTargetState | None = None,
    ) -> Sequence[DeletionTarget]:
        statement = select(DeletionTargetRow).where(
            DeletionTargetRow.owner_id == scope.owner_id,
            DeletionTargetRow.operation_id == operation_id,
        )
        if state is not None:
            statement = statement.where(DeletionTargetRow.state == state.value)
        with translate_database_errors("list deletion targets"):
            rows = self._session.scalars(
                statement.order_by(
                    DeletionTargetRow.direct.desc(),
                    DeletionTargetRow.target_kind,
                    DeletionTargetRow.target_id,
                ).execution_options(populate_existing=True)
            ).all()
        return [_target(row) for row in rows]

    def record_target(
        self,
        scope: OwnerScope,
        operation_id: uuid.UUID,
        target_kind: DeletionTargetKind,
        target_id: uuid.UUID,
        state: DeletionTargetState,
        *,
        expected: DeletionTargetState,
        error_code: str | None = None,
    ) -> None:
        if not expected.can_move_to(state):
            raise DomainValidationError(f"a deletion target cannot move from {expected} to {state}")
        # Validates the error code against the state with the domain rules.
        DeletionTarget(
            target_kind=target_kind,
            target_id=target_id,
            action=DeletionAction.DELETE,
            direct=False,
            state=state,
            error_code=error_code,
        )
        values: dict[str, object] = {"state": state.value, "error_code": error_code}
        if state in (DeletionTargetState.PROPAGATED, DeletionTargetState.FAILED):
            values["attempts"] = DeletionTargetRow.attempts + 1
        with translate_database_errors("record deletion target"):
            operation = self.get(scope, operation_id)
            if operation is not None and operation.status.finished:
                raise DomainValidationError("a finished deletion operation is not changed")
            conditional_update(
                self._session,
                update(DeletionTargetRow)
                .where(
                    DeletionTargetRow.owner_id == scope.owner_id,
                    DeletionTargetRow.operation_id == operation_id,
                    DeletionTargetRow.target_kind == target_kind.value,
                    DeletionTargetRow.target_id == target_id,
                    DeletionTargetRow.state == expected.value,
                )
                .values(**values),
                exists=select(DeletionTargetRow.id)
                .where(
                    DeletionTargetRow.owner_id == scope.owner_id,
                    DeletionTargetRow.operation_id == operation_id,
                    DeletionTargetRow.target_kind == target_kind.value,
                    DeletionTargetRow.target_id == target_id,
                )
                .exists(),
                what="deletion target",
            )

    def set_status(
        self,
        scope: OwnerScope,
        operation_id: uuid.UUID,
        status: DeletionOperationStatus,
        *,
        expected: DeletionOperationStatus,
        at: datetime,
        error_code: str | None = None,
    ) -> DeletionOperation:
        _require_aware(at)
        with translate_database_errors("set deletion operation status"):
            if status is DeletionOperationStatus.COMPLETED:
                unverified = self._session.scalar(
                    select(func.count())
                    .select_from(DeletionTargetRow)
                    .where(
                        DeletionTargetRow.owner_id == scope.owner_id,
                        DeletionTargetRow.operation_id == operation_id,
                        DeletionTargetRow.state != DeletionTargetState.VERIFIED.value,
                    )
                )
                if unverified:
                    raise DomainValidationError(
                        "a deletion is complete only when every target is verified"
                    )
            conditional_update(
                self._session,
                update(DeletionOperationRow)
                .where(
                    DeletionOperationRow.id == operation_id,
                    DeletionOperationRow.owner_id == scope.owner_id,
                    DeletionOperationRow.status == expected.value,
                )
                .values(
                    status=status.value,
                    finished_at=at if status.finished else None,
                    error_code=error_code,
                ),
                exists=select(DeletionOperationRow.id)
                .where(
                    DeletionOperationRow.id == operation_id,
                    DeletionOperationRow.owner_id == scope.owner_id,
                )
                .exists(),
                what="deletion operation",
            )
        updated = self.get(scope, operation_id)
        if updated is None:  # pragma: no cover - updated in this transaction
            raise RecordNotFoundError("deletion operation not found")
        return updated

    def unfinished(self, scope: OwnerScope) -> Sequence[DeletionOperation]:
        finished = [s.value for s in DeletionOperationStatus if s.finished]
        with translate_database_errors("list unfinished deletion operations"):
            rows = self._session.scalars(
                select(DeletionOperationRow)
                .where(
                    DeletionOperationRow.owner_id == scope.owner_id,
                    DeletionOperationRow.status.not_in(finished),
                )
                .order_by(DeletionOperationRow.requested_at, DeletionOperationRow.id)
                .execution_options(populate_existing=True)
            ).all()
        return [_operation(row) for row in rows]

    def operations_for(
        self, scope: OwnerScope, target_kind: DeletionTargetKind, target_id: uuid.UUID
    ) -> Sequence[DeletionOperation]:
        with translate_database_errors("find deletion operations for record"):
            rows = self._session.scalars(
                select(DeletionOperationRow)
                .join(
                    DeletionTargetRow,
                    (DeletionTargetRow.operation_id == DeletionOperationRow.id)
                    & (DeletionTargetRow.owner_id == DeletionOperationRow.owner_id),
                )
                .where(
                    DeletionOperationRow.owner_id == scope.owner_id,
                    DeletionTargetRow.target_kind == target_kind.value,
                    DeletionTargetRow.target_id == target_id,
                )
                .order_by(DeletionOperationRow.requested_at, DeletionOperationRow.id)
            ).all()
        return [_operation(row) for row in rows]

    def _insert_targets(
        self, scope: OwnerScope, operation_id: uuid.UUID, targets: Sequence[DeletionTarget]
    ) -> int:
        added = 0
        for target in targets:
            inserted = self._session.scalar(
                pg_insert(DeletionTargetRow)
                .values(
                    id=uuid.uuid4(),
                    owner_id=scope.owner_id,
                    operation_id=operation_id,
                    target_kind=target.target_kind.value,
                    target_id=target.target_id,
                    direct=target.direct,
                    action=target.action.value,
                    state=target.state.value,
                    attempts=target.attempts,
                )
                .on_conflict_do_nothing(index_elements=["operation_id", "target_kind", "target_id"])
                .returning(DeletionTargetRow.id)
            )
            added += inserted is not None
        return added


def _require_new_targets(targets: Sequence[DeletionTarget]) -> None:
    if any(t.state is not DeletionTargetState.PENDING or t.attempts for t in targets):
        raise DomainValidationError("new deletion targets are pending with no attempts")
    keys = [(t.target_kind, t.target_id) for t in targets]
    if len(set(keys)) != len(keys):
        raise DomainValidationError("each record appears once in a deletion ledger")
