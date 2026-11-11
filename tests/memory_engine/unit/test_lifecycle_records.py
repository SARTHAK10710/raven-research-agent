"""Phase 8.2 step 5 domain records: invariants checked without a database."""

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from memory_engine.domain.errors import DomainValidationError
from memory_engine.domain.identifiers import new_id
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
from memory_engine.personal.domain import (
    CandidateEvaluation,
    CorrectionRequest,
    CorrectionTarget,
    DeletionOperation,
    DeletionTarget,
    SourceProcessingEvent,
)

T0 = datetime(2026, 11, 1, 9, 0, tzinfo=UTC)
OWNER = new_id()


def _event(**overrides: Any) -> SourceProcessingEvent:
    values: dict[str, Any] = {
        "id": new_id(),
        "owner_id": OWNER,
        "source_id": new_id(),
        "event_type": ProcessingEventType.TRANSITION,
        "from_status": SourceProcessingStatus.QUEUED,
        "to_status": SourceProcessingStatus.PROCESSING,
        "attempt": 1,
        "occurred_at": T0,
    }
    return SourceProcessingEvent(**{**values, **overrides})


def _evaluation(**overrides: Any) -> CandidateEvaluation:
    values: dict[str, Any] = {
        "id": new_id(),
        "owner_id": OWNER,
        "candidate_id": new_id(),
        "outcome": EvaluationOutcome.PROCEED,
        "from_status": CandidateStatus.CANDIDATE,
        "to_status": CandidateStatus.VALIDATED,
        "method": "memory_evaluation",
        "method_version": "1",
        "evaluated_at": T0,
    }
    return CandidateEvaluation(**{**values, **overrides})


def _correction(**overrides: Any) -> CorrectionRequest:
    values: dict[str, Any] = {
        "id": new_id(),
        "owner_id": OWNER,
        "status": CorrectionStatus.OPEN,
        "requested_at": T0,
        "proposed_change": {"value": "light"},
    }
    return CorrectionRequest(**{**values, **overrides})


def _operation(**overrides: Any) -> DeletionOperation:
    values: dict[str, Any] = {
        "id": new_id(),
        "owner_id": OWNER,
        "request_kind": DeletionRequestKind.USER_REQUEST,
        "status": DeletionOperationStatus.REQUESTED,
        "idempotency_key": "forget-1",
        "requested_at": T0,
    }
    return DeletionOperation(**{**values, **overrides})


# --- processing events -------------------------------------------------------------


def test_a_processing_event_changes_the_status() -> None:
    with pytest.raises(DomainValidationError, match="changes"):
        _event(to_status=SourceProcessingStatus.QUEUED)


def test_only_failures_carry_an_error_code() -> None:
    failure = _event(
        event_type=ProcessingEventType.FAILURE,
        to_status=SourceProcessingStatus.PROCESSING_FAILED,
        error_code="PARSER_CRASHED",
    )
    assert failure.error_code == "PARSER_CRASHED"
    with pytest.raises(DomainValidationError):
        _event(event_type=ProcessingEventType.FAILURE)
    with pytest.raises(DomainValidationError):
        _event(error_code="PARSER_CRASHED")


@pytest.mark.parametrize("code", ["parser crashed", "1BAD", "", "A" * 65, "Contains user text"])
def test_error_codes_are_codes_not_text(code: str) -> None:
    with pytest.raises(DomainValidationError):
        _event(event_type=ProcessingEventType.FAILURE, error_code=code)


def test_attempts_start_at_one_and_times_are_aware() -> None:
    with pytest.raises(DomainValidationError):
        _event(attempt=0)
    with pytest.raises(DomainValidationError):
        _event(occurred_at=datetime(2026, 11, 1))  # deliberately naive


# --- evaluations --------------------------------------------------------------------


@pytest.mark.parametrize(
    ("outcome", "allowed"),
    [
        (EvaluationOutcome.PROCEED, {CandidateStatus.CANDIDATE, CandidateStatus.VALIDATED}),
        (EvaluationOutcome.NEEDS_REVIEW, {CandidateStatus.NEEDS_REVIEW}),
        (EvaluationOutcome.REJECT, {CandidateStatus.REJECTED}),
        (EvaluationOutcome.DEFER, {CandidateStatus.CANDIDATE}),
    ],
)
def test_evaluation_outcomes_limit_the_resulting_status(
    outcome: EvaluationOutcome, allowed: set[CandidateStatus]
) -> None:
    assert outcome.allowed_statuses() == allowed
    for status in CandidateStatus:
        if status in allowed:
            assert _evaluation(outcome=outcome, to_status=status).to_status is status
        else:
            with pytest.raises(DomainValidationError):
                _evaluation(outcome=outcome, to_status=status)


def test_evaluations_validate_scores_method_and_reason() -> None:
    assert _evaluation(importance=0.0, confidence=1.0, reason_code="LOW_UTILITY").importance == 0
    for overrides in (
        {"importance": 1.5},
        {"confidence": -0.1},
        {"method": " "},
        {"method_version": ""},
        {"reason_code": "low utility"},
    ):
        with pytest.raises(DomainValidationError):
            _evaluation(**overrides)


# --- corrections --------------------------------------------------------------------


def test_an_open_correction_proposes_a_change_and_is_unresolved() -> None:
    request = _correction(evidence={"memory_ids": ["m1"]})
    assert dict(request.proposed_change or {}) == {"value": "light"}
    with pytest.raises(TypeError):
        request.proposed_change["value"] = "x"  # type: ignore[index]
    with pytest.raises(DomainValidationError):
        _correction(proposed_change={})
    with pytest.raises(DomainValidationError):
        _correction(resolved_at=T0)
    with pytest.raises(DomainValidationError):
        _correction(resolution_note="Too early.")


def test_resolved_corrections_record_when_and_not_before_the_request() -> None:
    for status in (
        CorrectionStatus.ACCEPTED,
        CorrectionStatus.REJECTED,
        CorrectionStatus.WITHDRAWN,
    ):
        assert status.resolved
        with pytest.raises(DomainValidationError):
            _correction(status=status)
        assert _correction(status=status, resolved_at=T0).status is status
    with pytest.raises(DomainValidationError):
        _correction(status=CorrectionStatus.REJECTED, resolved_at=T0 - timedelta(days=1))
    with pytest.raises(DomainValidationError):
        _correction(status=CorrectionStatus.REJECTED, resolved_at=T0, resolution_note=" ")


def test_a_deleted_correction_keeps_no_content() -> None:
    deleted = _correction(status=CorrectionStatus.DELETED, proposed_change=None)
    assert deleted.proposed_change is None and not deleted.evidence
    assert not CorrectionStatus.DELETED.resolved and not CorrectionStatus.OPEN.resolved
    cases: tuple[dict[str, Any], ...] = (
        {"proposed_change": {"value": "x"}},
        {"proposed_change": None, "evidence": {"ids": []}},
        {"proposed_change": None, "resolution_note": "kept"},
    )
    for overrides in cases:
        with pytest.raises(DomainValidationError):
            _correction(status=CorrectionStatus.DELETED, **overrides)


def test_correction_targets_are_applied_by_a_later_revision() -> None:
    assert (
        CorrectionTarget(memory_id=new_id(), base_revision_number=1).applied_revision_number is None
    )
    assert (
        CorrectionTarget(
            memory_id=new_id(), base_revision_number=1, applied_revision_number=2
        ).applied_revision_number
        == 2
    )
    for base, applied in ((0, None), (2, 2), (3, 1)):
        with pytest.raises(DomainValidationError):
            CorrectionTarget(
                memory_id=new_id(), base_revision_number=base, applied_revision_number=applied
            )


# --- deletion ------------------------------------------------------------------------


def test_a_deletion_is_finished_exactly_when_it_records_a_finish_time() -> None:
    finished = {
        DeletionOperationStatus.COMPLETED,
        DeletionOperationStatus.PARTIALLY_COMPLETED,
        DeletionOperationStatus.FAILED,
    }
    assert {s for s in DeletionOperationStatus if s.finished} == finished
    for status in DeletionOperationStatus:
        code = "PROPAGATION_FAILED" if status is DeletionOperationStatus.FAILED else None
        if status in finished:
            assert _operation(status=status, finished_at=T0, error_code=code).finished_at == T0
            with pytest.raises(DomainValidationError):
                _operation(status=status, error_code=code)
        else:
            with pytest.raises(DomainValidationError):
                _operation(status=status, finished_at=T0)


def test_failed_deletions_carry_a_code_and_completed_ones_none() -> None:
    with pytest.raises(DomainValidationError):
        _operation(status=DeletionOperationStatus.FAILED, finished_at=T0)
    with pytest.raises(DomainValidationError):
        _operation(status=DeletionOperationStatus.COMPLETED, finished_at=T0, error_code="X")
    with pytest.raises(DomainValidationError):
        _operation(finished_at=None, requested_at=T0, idempotency_key=" ")
    with pytest.raises(DomainValidationError):
        _operation(idempotency_key="k" * 201)
    with pytest.raises(DomainValidationError):
        _operation(status=DeletionOperationStatus.COMPLETED, finished_at=T0 - timedelta(seconds=1))


def test_deletion_target_progress_rules() -> None:
    pending, propagated, verified, failed = (
        DeletionTargetState.PENDING,
        DeletionTargetState.PROPAGATED,
        DeletionTargetState.VERIFIED,
        DeletionTargetState.FAILED,
    )
    allowed = {
        (pending, propagated),
        (pending, failed),
        (propagated, verified),
        (propagated, failed),
        (failed, pending),
    }
    for source in DeletionTargetState:
        for target in DeletionTargetState:
            assert source.can_move_to(target) == ((source, target) in allowed)


def test_deletion_targets_hold_identifiers_and_safe_codes_only() -> None:
    target = DeletionTarget(
        target_kind=DeletionTargetKind.ATOMIC_MEMORY,
        target_id=new_id(),
        action=DeletionAction.DELETE,
        direct=True,
    )
    assert target.state is DeletionTargetState.PENDING and target.attempts == 0
    for overrides in (
        {"attempts": -1},
        {"state": DeletionTargetState.FAILED},
        {"error_code": "INDEX_DOWN"},
        {"state": DeletionTargetState.FAILED, "error_code": "index down"},
    ):
        with pytest.raises(DomainValidationError):
            DeletionTarget(
                target_kind=DeletionTargetKind.ATOMIC_MEMORY,
                target_id=new_id(),
                action=DeletionAction.DELETE,
                direct=True,
                **overrides,
            )
