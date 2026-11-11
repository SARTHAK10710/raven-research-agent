"""Phase 8.4 step 1: worker rules without infrastructure (deferral, results, parsing)."""

import json
import uuid
from datetime import UTC, datetime
from typing import Any

import pytest

from memory_engine.config.settings import ExtractionSettings
from memory_engine.domain.errors import DomainValidationError
from memory_engine.domain.vocabulary import (
    CandidateOrigin,
    CandidateStatus,
    ProcessingEventType,
    SourceProcessingStatus,
)
from memory_engine.infrastructure.messaging import retry_delay
from memory_engine.personal.application.extraction import (
    ExtractionOutcome,
    ExtractionReport,
    PipelineResult,
    parse_segments,
)
from memory_engine.personal.application.language import (
    LanguagePolicy,
    assess,
)
from memory_engine.personal.domain import MemoryCandidate, SourceProcessingEvent

T0 = datetime(2026, 11, 12, 9, 0, tzinfo=UTC)
OWNER = uuid.uuid4()


def _event(to: SourceProcessingStatus, **extra: Any) -> SourceProcessingEvent:
    values: dict[str, Any] = {
        "id": uuid.uuid4(),
        "owner_id": OWNER,
        "source_id": uuid.uuid4(),
        "event_type": ProcessingEventType.TRANSITION,
        "from_status": SourceProcessingStatus.PROCESSING,
        "to_status": to,
        "attempt": 1,
        "occurred_at": T0,
    }
    return SourceProcessingEvent(**values | extra)


def test_deferral_and_rejection_need_a_reason_code() -> None:
    assert _event(SourceProcessingStatus.DEFERRED, reason_code="UNSUPPORTED_LANGUAGE")
    assert _event(SourceProcessingStatus.REJECTED, reason_code="NOT_RELEVANT")
    for status in (SourceProcessingStatus.DEFERRED, SourceProcessingStatus.REJECTED):
        with pytest.raises(DomainValidationError, match="reason_code"):
            _event(status)
    with pytest.raises(DomainValidationError, match="reason_code"):
        _event(SourceProcessingStatus.EXTRACTED, reason_code="WHY")
    with pytest.raises(DomainValidationError):
        _event(SourceProcessingStatus.DEFERRED, reason_code="not a code")


def test_only_deferred_and_rejected_need_reasons() -> None:
    assert {s for s in SourceProcessingStatus if s.needs_reason} == {
        SourceProcessingStatus.DEFERRED,
        SourceProcessingStatus.REJECTED,
    }


def _candidate() -> MemoryCandidate:
    return MemoryCandidate(
        id=uuid.uuid4(),
        owner_id=OWNER,
        source_id=uuid.uuid4(),
        proposition="Synthetic proposition.",
        status=CandidateStatus.CANDIDATE,
        origin=CandidateOrigin.EXPLICIT,
    )


@pytest.mark.parametrize(
    "values",
    [
        {"status": SourceProcessingStatus.PROCESSING_FAILED},
        {"status": SourceProcessingStatus.QUEUED},
        {"status": SourceProcessingStatus.DEFERRED},
        {"status": SourceProcessingStatus.EXTRACTED, "reason_code": "WHY"},
        {
            "status": SourceProcessingStatus.REJECTED,
            "reason_code": "NOT_RELEVANT",
            "candidates": [_candidate()],
        },
    ],
)
def test_a_pipeline_result_must_be_consistent(values: dict[str, Any]) -> None:
    with pytest.raises(DomainValidationError):
        PipelineResult(**values)


def test_valid_pipeline_results() -> None:
    assert PipelineResult(status=SourceProcessingStatus.EXTRACTED, candidates=[_candidate()])
    assert PipelineResult(status=SourceProcessingStatus.PARTIALLY_EXTRACTED)
    assert PipelineResult(status=SourceProcessingStatus.DEFERRED, reason_code="LATER")


def _normalized(**content: Any) -> bytes:
    return json.dumps({"normalization_version": "1", **content}).encode()


def test_normalized_text_and_conversations_become_segments() -> None:
    [segment] = parse_segments(_normalized(text="I like tea."))
    assert (segment.position, segment.text, segment.from_user) == (0, "I like tea.", True)
    messages = [
        {"position": 0, "speaker": "Sam", "from_user": True, "text": "Hi", "sent_at": None},
        {"position": 1, "speaker": "Raven", "from_user": False, "text": "Hello"},
    ]
    segments = parse_segments(_normalized(messages=messages))
    assert [(s.speaker, s.from_user) for s in segments] == [("Sam", True), ("Raven", False)]


@pytest.mark.parametrize(
    "data",
    [
        b"\xff\xfe",
        b"not json",
        b"[]",
        json.dumps({"normalization_version": "2", "text": "x"}).encode(),
        _normalized(messages=[]),
        _normalized(messages=["x"]),
        _normalized(messages=[{"text": 3}]),
        _normalized(other="x"),
    ],
)
def test_unreadable_normalized_content_is_refused(data: bytes) -> None:
    with pytest.raises(DomainValidationError):
        parse_segments(data)


def test_reports_serialize_identifiers_and_codes_only() -> None:
    report = ExtractionReport(
        outcome=ExtractionOutcome.COMPLETED,
        source_id=OWNER,
        status=SourceProcessingStatus.DEFERRED,
        reason_code="UNSUPPORTED_LANGUAGE",
    )
    assert report.as_dict() == {
        "outcome": "completed",
        "source_id": str(OWNER),
        "status": "deferred",
        "candidates": 0,
        "reason_code": "UNSUPPORTED_LANGUAGE",
        "error_code": None,
    }


def test_task_retry_delays_double_and_are_capped() -> None:
    settings = ExtractionSettings()
    assert [retry_delay(n, settings) for n in range(4)] == [2.0, 4.0, 8.0, 16.0]
    assert retry_delay(50, settings) == 300.0


def test_language_policy_edges() -> None:
    policy = LanguagePolicy(
        min_words=3, min_function_word_share=0.2, max_non_latin_letter_share=0.3
    )
    assert assess([""], policy).english  # nothing to judge
    assert assess(["12345 !!!"], policy).english
    result = assess(["the cat sat"], policy)
    assert result.english and result.function_word_share == pytest.approx(1 / 3)
    assert not assess(["gato perro casa mesa"], policy).english
