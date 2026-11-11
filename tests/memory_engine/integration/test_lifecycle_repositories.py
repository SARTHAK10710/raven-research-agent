"""Plan 8.2 step 5: processing, evaluation, correction and deletion records (real PostgreSQL).

``build`` is the synthetic-record fixture from conftest.py; all content is synthetic.
"""

import uuid
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy import Connection, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from memory_engine.domain.errors import DomainValidationError, OwnershipError
from memory_engine.domain.identifiers import OwnerScope, new_id
from memory_engine.domain.vocabulary import (
    CandidateOrigin,
    CandidateStatus,
    CorrectionStatus,
    DeletionAction,
    DeletionOperationStatus,
    DeletionRequestKind,
    DeletionTargetKind,
    DeletionTargetState,
    EvaluationOutcome,
    ProcessingEventType,
    RevisionChangeType,
    SourceProcessingStatus,
)
from memory_engine.exceptions import (
    ConcurrencyConflictError,
    PersistenceError,
    RecordNotFoundError,
)
from memory_engine.infrastructure.persistence import SqlAlchemyPersonalUnitOfWorkFactory
from memory_engine.personal.domain import (
    CandidateEvaluation,
    CorrectionRequest,
    CorrectionTarget,
    DeletionOperation,
    DeletionTarget,
    SourceProcessingEvent,
)

pytestmark = pytest.mark.integration

Uow = SqlAlchemyPersonalUnitOfWorkFactory
T0 = datetime(2026, 11, 1, 9, 0, tzinfo=UTC)
Status = SourceProcessingStatus


def _event(
    owner: OwnerScope,
    source_id: uuid.UUID,
    from_status: SourceProcessingStatus,
    to_status: SourceProcessingStatus,
    *,
    event_type: ProcessingEventType = ProcessingEventType.TRANSITION,
    attempt: int = 1,
    minutes: int = 0,
    error_code: str | None = None,
) -> SourceProcessingEvent:
    return SourceProcessingEvent(
        id=new_id(),
        owner_id=owner.owner_id,
        source_id=source_id,
        event_type=event_type,
        from_status=from_status,
        to_status=to_status,
        attempt=attempt,
        occurred_at=T0 + timedelta(minutes=minutes),
        error_code=error_code,
    )


def _evaluation(
    owner: OwnerScope,
    candidate_id: uuid.UUID,
    outcome: EvaluationOutcome,
    from_status: CandidateStatus,
    to_status: CandidateStatus,
    **extra: Any,
) -> CandidateEvaluation:
    return CandidateEvaluation(
        id=new_id(),
        owner_id=owner.owner_id,
        candidate_id=candidate_id,
        outcome=outcome,
        from_status=from_status,
        to_status=to_status,
        method="memory_evaluation",
        method_version="1",
        evaluated_at=extra.pop("evaluated_at", T0),
        **extra,
    )


def _source(uow_factory: Uow, owner: OwnerScope, build: Any, status: Status) -> Any:
    source = replace(build.source(owner), processing_status=status)
    with uow_factory() as uow:
        uow.sources.add(owner, source)
    return source


def _candidate(uow_factory: Uow, owner: OwnerScope, build: Any, **changes: Any) -> Any:
    source = build.source(owner)
    candidate = replace(build.candidate(owner, source.id), status=CandidateStatus.CANDIDATE)
    candidate = replace(candidate, **changes)
    with uow_factory() as uow:
        uow.sources.add(owner, source)
        uow.candidates.add(owner, candidate)
    return candidate


def _memory(uow_factory: Uow, owner: OwnerScope, build: Any, content: str = "A fact.") -> Any:
    memory, revision = build.memory(owner, content)
    with uow_factory() as uow:
        uow.memories.add(owner, memory, revision)
    return memory


def _correction(owner: OwnerScope, **overrides: Any) -> CorrectionRequest:
    values: dict[str, Any] = {
        "id": new_id(),
        "owner_id": owner.owner_id,
        "status": CorrectionStatus.OPEN,
        "requested_at": T0,
        "proposed_change": {"value": "light"},
        "evidence": {"source_ids": ["synthetic-source"]},
    }
    return CorrectionRequest(**{**values, **overrides})


def _operation(owner: OwnerScope, key: str = "forget-1") -> DeletionOperation:
    return DeletionOperation(
        id=new_id(),
        owner_id=owner.owner_id,
        request_kind=DeletionRequestKind.USER_REQUEST,
        status=DeletionOperationStatus.REQUESTED,
        idempotency_key=key,
        requested_at=T0,
    )


def _target(
    kind: DeletionTargetKind, target_id: uuid.UUID, *, direct: bool = True
) -> DeletionTarget:
    return DeletionTarget(
        target_kind=kind,
        target_id=target_id,
        action=DeletionAction.DELETE if direct else DeletionAction.INVALIDATE,
        direct=direct,
    )


# --- source processing events --------------------------------------------------------


def test_source_transitions_keep_failures_retries_and_order(
    uow_factory: Uow, owner: OwnerScope, build: Any
) -> None:
    source = _source(uow_factory, owner, build, Status.QUEUED)
    events = [
        _event(owner, source.id, Status.QUEUED, Status.PROCESSING),
        _event(
            owner,
            source.id,
            Status.PROCESSING,
            Status.PROCESSING_FAILED,
            event_type=ProcessingEventType.FAILURE,
            error_code="EXTRACTOR_TIMEOUT",
        ),
        _event(
            owner,
            source.id,
            Status.PROCESSING_FAILED,
            Status.QUEUED,
            event_type=ProcessingEventType.RETRY,
            attempt=2,
        ),
    ]
    with uow_factory() as uow:
        # Same timestamp for all: order must come from insertion (seq), not the clock.
        for event in events:
            uow.processing.transition(owner, event)
    with uow_factory() as uow:
        uow.processing.transition(
            owner, _event(owner, source.id, Status.QUEUED, Status.PROCESSING, attempt=2)
        )
        uow.processing.transition(
            owner, _event(owner, source.id, Status.PROCESSING, Status.EXTRACTED, attempt=2)
        )
        stored = uow.sources.get(owner, source.id)
        history = uow.processing.events(owner, source.id)
    assert stored is not None and stored.processing_status is Status.EXTRACTED
    assert [e.id for e in history[:3]] == [e.id for e in events]
    assert [e.to_status for e in history][-1] is Status.EXTRACTED
    assert history[1].error_code == "EXTRACTOR_TIMEOUT"


def test_stale_or_foreign_transitions_write_nothing(
    uow_factory: Uow, owner: OwnerScope, other_owner: OwnerScope, build: Any
) -> None:
    source = _source(uow_factory, owner, build, Status.QUEUED)
    with pytest.raises(ConcurrencyConflictError), uow_factory() as uow:
        uow.processing.transition(
            owner, _event(owner, source.id, Status.PROCESSING, Status.EXTRACTED)
        )
    with pytest.raises(RecordNotFoundError), uow_factory() as uow:
        uow.processing.transition(
            other_owner, _event(other_owner, source.id, Status.QUEUED, Status.PROCESSING)
        )
    with pytest.raises(OwnershipError), uow_factory() as uow:
        uow.processing.transition(
            owner, _event(other_owner, source.id, Status.QUEUED, Status.PROCESSING)
        )
    with uow_factory() as uow:
        assert uow.processing.events(owner, source.id) == []
        assert uow.processing.events(other_owner, source.id) == []
        stored = uow.sources.get(owner, source.id)
    assert stored is not None and stored.processing_status is Status.QUEUED


def test_processing_history_and_source_identity_are_protected(
    connection: Connection, uow_factory: Uow, owner: OwnerScope, build: Any
) -> None:
    source = _source(uow_factory, owner, build, Status.QUEUED)
    with uow_factory() as uow:
        uow.processing.transition(owner, _event(owner, source.id, Status.QUEUED, Status.PROCESSING))
    with pytest.raises(DBAPIError, match="immutable columns"):
        connection.execute(
            text("UPDATE memory.pm_memory_source SET source_type = 'conversation' WHERE id = :s"),
            {"s": source.id},
        )


def test_processing_events_are_append_only(
    connection: Connection, uow_factory: Uow, owner: OwnerScope, build: Any
) -> None:
    source = _source(uow_factory, owner, build, Status.QUEUED)
    with uow_factory() as uow:
        uow.processing.transition(owner, _event(owner, source.id, Status.QUEUED, Status.PROCESSING))
    with pytest.raises(DBAPIError, match="immutable columns"):
        connection.execute(
            text("UPDATE memory.pm_source_processing_event SET attempt = 9 WHERE source_id = :s"),
            {"s": source.id},
        )


def test_a_failure_event_needs_an_error_code_in_the_database(
    connection: Connection, uow_factory: Uow, owner: OwnerScope, build: Any
) -> None:
    source = _source(uow_factory, owner, build, Status.PROCESSING)
    with pytest.raises(IntegrityError, match="ck_pm_source_processing_event_failure_code"):
        connection.execute(
            text(
                "INSERT INTO memory.pm_source_processing_event (id, owner_id, source_id,"
                " event_type, from_status, to_status, attempt, occurred_at) VALUES"
                " (:id, :owner, :s, 'failure', 'processing', 'processing_failed', 1, now())"
            ),
            {"id": new_id(), "owner": owner.owner_id, "s": source.id},
        )


# --- candidate evaluation ------------------------------------------------------------


def test_evaluation_updates_the_latest_state_and_keeps_history(
    uow_factory: Uow, owner: OwnerScope, build: Any
) -> None:
    candidate = _candidate(uow_factory, owner, build)
    deferred = _evaluation(
        owner,
        candidate.id,
        EvaluationOutcome.DEFER,
        CandidateStatus.CANDIDATE,
        CandidateStatus.CANDIDATE,
        reason_code="AWAITING_CONTEXT",
    )
    proceeded = _evaluation(
        owner,
        candidate.id,
        EvaluationOutcome.PROCEED,
        CandidateStatus.CANDIDATE,
        CandidateStatus.VALIDATED,
        importance=0.7,
    )
    with uow_factory() as uow:
        uow.evaluations.record(owner, deferred)
        uow.evaluations.record(owner, proceeded)
    with uow_factory() as uow:
        stored = uow.candidates.get(owner, candidate.id)
        history = uow.evaluations.history(owner, candidate.id)
    assert stored is not None
    assert stored.status is CandidateStatus.VALIDATED
    assert stored.importance == 0.7
    assert stored.confidence == candidate.confidence  # not carried by the evaluation: kept
    assert [e.id for e in history] == [deferred.id, proceeded.id]
    assert history[0].reason_code == "AWAITING_CONTEXT"


def test_stale_evaluation_writes_no_history(
    uow_factory: Uow, owner: OwnerScope, other_owner: OwnerScope, build: Any
) -> None:
    candidate = _candidate(uow_factory, owner, build)
    stale = _evaluation(
        owner,
        candidate.id,
        EvaluationOutcome.REJECT,
        CandidateStatus.NEEDS_REVIEW,
        CandidateStatus.REJECTED,
    )
    with pytest.raises(ConcurrencyConflictError), uow_factory() as uow:
        uow.evaluations.record(owner, stale)
    foreign = _evaluation(
        other_owner,
        candidate.id,
        EvaluationOutcome.REJECT,
        CandidateStatus.CANDIDATE,
        CandidateStatus.REJECTED,
    )
    with pytest.raises(RecordNotFoundError), uow_factory() as uow:
        uow.evaluations.record(other_owner, foreign)
    with uow_factory() as uow:
        assert uow.evaluations.history(owner, candidate.id) == []
        assert uow.evaluations.history(other_owner, candidate.id) == []


def test_unresolved_origin_cannot_be_validated_by_an_evaluation(
    uow_factory: Uow, owner: OwnerScope, build: Any
) -> None:
    candidate = _candidate(uow_factory, owner, build, origin=CandidateOrigin.UNRESOLVED)
    with pytest.raises(PersistenceError) as caught, uow_factory() as uow:
        uow.evaluations.record(
            owner,
            _evaluation(
                owner,
                candidate.id,
                EvaluationOutcome.PROCEED,
                CandidateStatus.CANDIDATE,
                CandidateStatus.VALIDATED,
            ),
        )
    assert caught.value.details["constraint"] == "ck_pm_memory_candidate_unresolved_not_validated"


def test_candidate_propositions_are_immutable(
    connection: Connection, uow_factory: Uow, owner: OwnerScope, build: Any
) -> None:
    candidate = _candidate(uow_factory, owner, build)
    with pytest.raises(DBAPIError, match="immutable columns"):
        connection.execute(
            text("UPDATE memory.pm_memory_candidate SET proposition = 'x' WHERE id = :c"),
            {"c": candidate.id},
        )


def test_the_database_ties_evaluation_outcomes_to_statuses(
    connection: Connection, uow_factory: Uow, owner: OwnerScope, build: Any
) -> None:
    candidate = _candidate(uow_factory, owner, build)
    with pytest.raises(IntegrityError, match="ck_pm_candidate_evaluation_outcome_status"):
        connection.execute(
            text(
                "INSERT INTO memory.pm_candidate_evaluation (id, owner_id, candidate_id, outcome,"
                " from_status, to_status, method, method_version, evaluated_at) VALUES"
                " (:id, :owner, :c, 'reject', 'candidate', 'validated', 'm', '1', now())"
            ),
            {"id": new_id(), "owner": owner.owner_id, "c": candidate.id},
        )


# --- corrections -----------------------------------------------------------------------


def test_accepted_correction_names_the_revisions_that_applied_it(
    uow_factory: Uow, owner: OwnerScope, build: Any
) -> None:
    memory, created = build.memory(owner, "Synthetic user prefers dark mode.")
    request = _correction(owner)
    with uow_factory() as uow:
        uow.memories.add(owner, memory, created)
        uow.corrections.open(
            owner, request, [CorrectionTarget(memory_id=memory.id, base_revision_number=1)]
        )
        assert [r.id for r in uow.corrections.open_for_memory(owner, memory.id)] == [request.id]
        corrected, revision = build.next_state(
            memory, RevisionChangeType.CORRECTED, content="Synthetic user prefers light mode."
        )
        uow.memories.apply_revision(owner, corrected, revision, expected_revision_number=1)
        resolved = uow.corrections.resolve(
            owner,
            request.id,
            CorrectionStatus.ACCEPTED,
            resolved_at=T0 + timedelta(days=1),
            applied={memory.id: 2},
        )
    assert resolved.status is CorrectionStatus.ACCEPTED
    assert resolved.proposed_change == {"value": "light"}
    with uow_factory() as uow:
        targets = uow.corrections.targets(owner, request.id)
        assert uow.corrections.open_for_memory(owner, memory.id) == []
    assert targets == [
        CorrectionTarget(memory_id=memory.id, base_revision_number=1, applied_revision_number=2)
    ]


def test_rejected_correction_never_changes_a_memory(
    uow_factory: Uow, owner: OwnerScope, build: Any
) -> None:
    memory = _memory(uow_factory, owner, build)
    request = _correction(owner)
    target = CorrectionTarget(memory_id=memory.id, base_revision_number=1)
    with uow_factory() as uow:
        uow.corrections.open(owner, request, [target])
    with pytest.raises(DomainValidationError), uow_factory() as uow:
        uow.corrections.resolve(
            owner, request.id, CorrectionStatus.REJECTED, resolved_at=T0, applied={memory.id: 2}
        )
    with pytest.raises(DomainValidationError), uow_factory() as uow:
        uow.corrections.resolve(owner, request.id, CorrectionStatus.ACCEPTED, resolved_at=T0)
    with pytest.raises(DomainValidationError), uow_factory() as uow:
        uow.corrections.resolve(
            owner, request.id, CorrectionStatus.ACCEPTED, resolved_at=T0, applied={new_id(): 2}
        )
    with pytest.raises(RecordNotFoundError), uow_factory() as uow:
        uow.corrections.resolve(
            owner, request.id, CorrectionStatus.ACCEPTED, resolved_at=T0, applied={memory.id: 5}
        )
    with uow_factory() as uow:
        resolved = uow.corrections.resolve(
            owner,
            request.id,
            CorrectionStatus.REJECTED,
            resolved_at=T0 + timedelta(hours=1),
            note="Contradicted by later evidence.",
        )
        stored = uow.memories.get(owner, memory.id)
        targets = uow.corrections.targets(owner, request.id)
    assert resolved.status is CorrectionStatus.REJECTED
    assert stored is not None and stored.revision_number == 1
    assert targets == [target]
    with pytest.raises(ConcurrencyConflictError), uow_factory() as uow:
        uow.corrections.resolve(owner, request.id, CorrectionStatus.WITHDRAWN, resolved_at=T0)


def test_corrections_need_live_memories_at_existing_revisions(
    uow_factory: Uow, owner: OwnerScope, other_owner: OwnerScope, build: Any
) -> None:
    mine = _memory(uow_factory, owner, build, "Mine.")
    theirs = _memory(uow_factory, other_owner, build, "Theirs.")
    for target in (
        CorrectionTarget(memory_id=theirs.id, base_revision_number=1),
        CorrectionTarget(memory_id=mine.id, base_revision_number=3),
    ):
        with pytest.raises(RecordNotFoundError), uow_factory() as uow:
            uow.corrections.open(owner, _correction(owner), [target])
    with pytest.raises(DomainValidationError), uow_factory() as uow:
        uow.corrections.open(owner, _correction(owner), [])
    request = _correction(owner)
    with uow_factory() as uow:
        uow.corrections.open(
            owner, request, [CorrectionTarget(memory_id=mine.id, base_revision_number=1)]
        )
    with uow_factory() as uow:
        assert uow.corrections.get(other_owner, request.id) is None
        assert uow.corrections.targets(other_owner, request.id) == []
    with pytest.raises(RecordNotFoundError), uow_factory() as uow:
        uow.corrections.resolve(other_owner, request.id, CorrectionStatus.WITHDRAWN, resolved_at=T0)


def test_purging_a_correction_drops_its_content_idempotently(
    connection: Connection, uow_factory: Uow, owner: OwnerScope, build: Any
) -> None:
    memory = _memory(uow_factory, owner, build)
    request = _correction(owner)
    with uow_factory() as uow:
        uow.corrections.open(
            owner, request, [CorrectionTarget(memory_id=memory.id, base_revision_number=1)]
        )
        uow.corrections.purge(owner, request.id)
        uow.corrections.purge(owner, request.id)
        assert uow.corrections.get(owner, request.id) is None
    row = connection.execute(
        text(
            "SELECT status, proposed_change, evidence, resolution_note"
            " FROM memory.pm_correction_request WHERE id = :r"
        ),
        {"r": request.id},
    ).one()
    assert tuple(row) == ("deleted", None, {}, None)
    with pytest.raises(RecordNotFoundError), uow_factory() as uow:
        uow.corrections.purge(owner, new_id())


def test_a_deleted_correction_cannot_keep_content_in_the_database(
    connection: Connection, owner: OwnerScope
) -> None:
    with pytest.raises(IntegrityError, match="ck_pm_correction_request_content_until_deleted"):
        connection.execute(
            text(
                "INSERT INTO memory.pm_correction_request (id, owner_id, status, proposed_change,"
                " requested_at) VALUES (:id, :owner, 'deleted', '{\"v\": 1}', now())"
            ),
            {"id": new_id(), "owner": owner.owner_id},
        )


# --- deletion operations -------------------------------------------------------------


def test_deletion_operations_are_idempotent_per_key(uow_factory: Uow, owner: OwnerScope) -> None:
    memory_id = new_id()
    operation = _operation(owner)
    with uow_factory() as uow:
        stored, created = uow.deletions.create(
            owner, operation, [_target(DeletionTargetKind.ATOMIC_MEMORY, memory_id)]
        )
        again, created_again = uow.deletions.create(
            owner,
            _operation(owner),  # same key, new id
            [_target(DeletionTargetKind.ATOMIC_MEMORY, new_id())],
        )
        targets = uow.deletions.targets(owner, operation.id)
    assert created and not created_again
    assert stored == operation and again == operation
    assert [t.target_id for t in targets] == [memory_id]


def test_deletion_completes_only_after_every_target_is_verified(
    uow_factory: Uow, owner: OwnerScope
) -> None:
    memory_id, membership_id = new_id(), new_id()
    operation = _operation(owner)
    memory = (DeletionTargetKind.ATOMIC_MEMORY, memory_id)
    membership = (DeletionTargetKind.EPISODE_MEMBERSHIP, membership_id)
    pending, propagated, verified, failed = (
        DeletionTargetState.PENDING,
        DeletionTargetState.PROPAGATED,
        DeletionTargetState.VERIFIED,
        DeletionTargetState.FAILED,
    )
    with uow_factory() as uow:
        uow.deletions.create(owner, operation, [_target(*memory)])
        dependency = _target(*membership, direct=False)
        assert uow.deletions.add_targets(owner, operation.id, [dependency]) == 1
        assert uow.deletions.add_targets(owner, operation.id, [dependency]) == 0
        uow.deletions.record_target(owner, operation.id, *memory, propagated, expected=pending)
        uow.deletions.record_target(owner, operation.id, *memory, verified, expected=propagated)
        uow.deletions.set_status(
            owner,
            operation.id,
            DeletionOperationStatus.PROPAGATING,
            expected=DeletionOperationStatus.REQUESTED,
            at=T0,
        )
    with (
        pytest.raises(DomainValidationError, match="every target is verified"),
        uow_factory() as uow,
    ):
        uow.deletions.set_status(
            owner,
            operation.id,
            DeletionOperationStatus.COMPLETED,
            expected=DeletionOperationStatus.PROPAGATING,
            at=T0,
        )
    with uow_factory() as uow:
        uow.deletions.record_target(
            owner,
            operation.id,
            *membership,
            failed,
            expected=pending,
            error_code="INDEX_UNAVAILABLE",
        )
        assert [t.target_id for t in uow.deletions.targets(owner, operation.id, state=failed)] == [
            membership_id
        ]
        uow.deletions.record_target(owner, operation.id, *membership, pending, expected=failed)
        uow.deletions.record_target(owner, operation.id, *membership, propagated, expected=pending)
        uow.deletions.record_target(owner, operation.id, *membership, verified, expected=propagated)
        done = uow.deletions.set_status(
            owner,
            operation.id,
            DeletionOperationStatus.COMPLETED,
            expected=DeletionOperationStatus.PROPAGATING,
            at=T0 + timedelta(minutes=5),
        )
        targets = {t.target_id: t for t in uow.deletions.targets(owner, operation.id)}
        assert uow.deletions.unfinished(owner) == []
    assert done.status is DeletionOperationStatus.COMPLETED
    assert done.finished_at == T0 + timedelta(minutes=5)
    assert targets[membership_id].attempts == 2 and targets[membership_id].error_code is None
    assert targets[memory_id].attempts == 1 and targets[memory_id].direct
    with pytest.raises(DomainValidationError), uow_factory() as uow:
        uow.deletions.add_targets(
            owner, operation.id, [_target(DeletionTargetKind.MEMORY_EMBEDDING, new_id())]
        )


def test_deletion_target_progress_follows_the_rules(uow_factory: Uow, owner: OwnerScope) -> None:
    memory = (DeletionTargetKind.ATOMIC_MEMORY, new_id())
    operation = _operation(owner)
    with uow_factory() as uow:
        uow.deletions.create(owner, operation, [_target(*memory)])
    with pytest.raises(DomainValidationError), uow_factory() as uow:
        uow.deletions.record_target(
            owner,
            operation.id,
            *memory,
            DeletionTargetState.VERIFIED,
            expected=DeletionTargetState.PENDING,
        )
    with pytest.raises(DomainValidationError), uow_factory() as uow:
        uow.deletions.record_target(
            owner,
            operation.id,
            *memory,
            DeletionTargetState.FAILED,
            expected=DeletionTargetState.PENDING,
        )
    with pytest.raises(ConcurrencyConflictError), uow_factory() as uow:
        uow.deletions.record_target(
            owner,
            operation.id,
            *memory,
            DeletionTargetState.VERIFIED,
            expected=DeletionTargetState.PROPAGATED,
        )
    with pytest.raises(RecordNotFoundError), uow_factory() as uow:
        uow.deletions.record_target(
            owner,
            operation.id,
            DeletionTargetKind.EPISODE,
            new_id(),
            DeletionTargetState.PROPAGATED,
            expected=DeletionTargetState.PENDING,
        )


def test_failed_and_unfinished_operations_stay_visible(uow_factory: Uow, owner: OwnerScope) -> None:
    # Distinct request times: "oldest first" is only defined between different times.
    first = _operation(owner, "forget-a")
    second = replace(_operation(owner, "forget-b"), requested_at=T0 + timedelta(minutes=1))
    with uow_factory() as uow:
        for operation in (first, second):
            uow.deletions.create(
                owner, operation, [_target(DeletionTargetKind.MEMORY_SOURCE, new_id())]
            )
        uow.deletions.set_status(
            owner,
            second.id,
            DeletionOperationStatus.REQUIRES_RECONCILIATION,
            expected=DeletionOperationStatus.REQUESTED,
            at=T0,
            error_code="OBJECT_STORE_UNAVAILABLE",
        )
        assert [o.id for o in uow.deletions.unfinished(owner)] == [first.id, second.id]
    with pytest.raises(PersistenceError) as caught, uow_factory() as uow:
        uow.deletions.set_status(
            owner,
            first.id,
            DeletionOperationStatus.FAILED,
            expected=DeletionOperationStatus.REQUESTED,
            at=T0,
        )
    assert caught.value.details["constraint"] == "ck_pm_deletion_operation_failure_code"


def test_the_ledger_outlives_records_and_stays_owner_scoped(
    uow_factory: Uow, owner: OwnerScope, other_owner: OwnerScope
) -> None:
    purged_id = new_id()  # no such record: the ledger has no foreign key to it
    operation = _operation(owner)
    with uow_factory() as uow:
        uow.deletions.create(
            owner, operation, [_target(DeletionTargetKind.MEMORY_CANDIDATE, purged_id)]
        )
    with uow_factory() as uow:
        found = uow.deletions.operations_for(owner, DeletionTargetKind.MEMORY_CANDIDATE, purged_id)
        assert [o.id for o in found] == [operation.id]
        assert (
            uow.deletions.operations_for(
                other_owner, DeletionTargetKind.MEMORY_CANDIDATE, purged_id
            )
            == []
        )
        assert uow.deletions.get(other_owner, operation.id) is None
        assert uow.deletions.targets(other_owner, operation.id) == []
        assert uow.deletions.unfinished(other_owner) == []
    with pytest.raises(OwnershipError), uow_factory() as uow:
        uow.deletions.create(
            other_owner, operation, [_target(DeletionTargetKind.MEMORY_CANDIDATE, purged_id)]
        )
    with pytest.raises(RecordNotFoundError), uow_factory() as uow:
        uow.deletions.add_targets(
            other_owner, operation.id, [_target(DeletionTargetKind.EPISODE, new_id())]
        )


def test_a_deletion_needs_a_direct_pending_target(uow_factory: Uow, owner: OwnerScope) -> None:
    dependency = _target(DeletionTargetKind.EPISODE, new_id(), direct=False)
    with pytest.raises(DomainValidationError), uow_factory() as uow:
        uow.deletions.create(owner, _operation(owner), [dependency])
    started = replace(
        _target(DeletionTargetKind.EPISODE, new_id()), state=DeletionTargetState.PROPAGATED
    )
    with pytest.raises(DomainValidationError), uow_factory() as uow:
        uow.deletions.create(owner, _operation(owner), [started])
    twice = _target(DeletionTargetKind.EPISODE, new_id())
    with pytest.raises(DomainValidationError), uow_factory() as uow:
        uow.deletions.create(owner, _operation(owner), [twice, twice])


def test_ledger_identity_is_immutable(
    connection: Connection, uow_factory: Uow, owner: OwnerScope
) -> None:
    operation = _operation(owner)
    with uow_factory() as uow:
        uow.deletions.create(owner, operation, [_target(DeletionTargetKind.ENTITY, new_id())])
    with pytest.raises(DBAPIError, match="immutable columns"):
        connection.execute(
            text("UPDATE memory.pm_deletion_target SET target_id = :t WHERE operation_id = :o"),
            {"t": new_id(), "o": operation.id},
        )
