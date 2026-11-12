"""Phase 8.4 step 2: the relevance gate (6.2.2) with the real spaCy analyzer, no I/O."""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

import pytest
from pydantic import ValidationError

from memory_engine.config.settings import RelevanceSettings
from memory_engine.domain.errors import DomainValidationError
from memory_engine.domain.vocabulary import (
    IngestionPriority,
    InstructionType,
    RelevanceOutcome,
    SourceProcessingStatus,
    SourceType,
)
from memory_engine.infrastructure.nlp import SpacySentenceAnalyzer
from memory_engine.personal.application.analysis import Sentence
from memory_engine.personal.application.extraction import (
    PipelineResult,
    Segment,
    SourceContent,
)
from memory_engine.personal.application.relevance import (
    ANALYSIS_UNAVAILABLE,
    METHOD,
    NO_USER_CONTENT,
    GatedPipeline,
    RelevanceGate,
    RelevancePolicy,
    SelectedSentence,
)
from memory_engine.personal.domain import MemorySource, RelevanceAssessment, UnitAssessment

T0 = datetime(2026, 11, 12, 9, 0, tzinfo=UTC)
ANALYZER = SpacySentenceAnalyzer()
POLICY = RelevancePolicy.from_settings(RelevanceSettings())


def _content(
    *segments: tuple[str, bool], instruction: InstructionType = InstructionType.NORMAL
) -> SourceContent:
    source = MemorySource(
        id=uuid.uuid4(),
        owner_id=uuid.uuid4(),
        source_type=SourceType.CONVERSATION if len(segments) > 1 else SourceType.TEXT,
        processing_status=SourceProcessingStatus.QUEUED,
        received_at=T0,
        content_sha256="a" * 64,
        instruction_type=instruction,
        priority=(
            IngestionPriority.NORMAL
            if instruction is InstructionType.NORMAL
            else IngestionPriority.HIGH
        ),
    )
    return SourceContent(
        source=source,
        segments=[Segment(position=i, text=t, from_user=u) for i, (t, u) in enumerate(segments)],
    )


def _gate(analyzer: Any = ANALYZER, **settings: Any) -> RelevanceGate:
    return RelevanceGate(
        analyzer, RelevancePolicy.from_settings(RelevanceSettings(**settings)), clock=lambda: T0
    )


def test_each_user_sentence_is_judged_and_relevant_ones_are_selected() -> None:
    decision = _gate().assess(
        _content(("Thanks! I prefer window seats. Should I learn Kotlin?", True))
    )
    assessment = decision.assessment
    assert [(u.sentence, u.outcome, u.reason_code) for u in assessment.units] == [
        (0, RelevanceOutcome.REJECT, "SMALL_TALK"),
        (1, RelevanceOutcome.PROCESS, None),
        (2, RelevanceOutcome.REJECT, "QUESTION_ONLY"),
    ]
    assert assessment.outcome is RelevanceOutcome.PROCESS and assessment.reason_code is None
    [selected] = decision.selected
    assert selected.sentence.text == "I prefer window seats."
    assert assessment.method == METHOD
    assert assessment.method_version.startswith("1+spacy-3.8.")
    assert "en_core_web_sm-3.8.0" in assessment.method_version


def test_assistant_turns_give_context_but_are_never_judged() -> None:
    assessment = (
        _gate()
        .assess(
            _content(
                ("I like hiking.", True),
                ("Where do you usually go hiking?", False),
                ("The Peak District.", True),
            )
        )
        .assessment
    )
    assert [u.segment for u in assessment.units] == [0, 2]
    answer = assessment.units[1]
    assert answer.signals["context"] == 1.0  # answers Raven's question
    assert answer.signals["personal"] == 0.6  # and is therefore about the user


def test_a_missing_signal_is_left_out_not_counted_as_zero() -> None:
    [unit] = _gate().assess(_content(("I prefer window seats.", True))).assessment.units
    assert "context" not in unit.signals  # a single text has no conversational context
    weights = POLICY.weights
    expected = sum(weights[k] * v for k, v in unit.signals.items()) / sum(
        weights[k] for k in unit.signals
    )
    assert unit.score == pytest.approx(expected, abs=1e-4)


def test_explicit_remember_protects_even_a_terse_input() -> None:
    assessment = (
        _gate()
        .assess(_content(("Tea, no sugar.", True), instruction=InstructionType.REMEMBER))
        .assessment
    )
    [unit] = assessment.units
    assert (unit.outcome, unit.protection) == (RelevanceOutcome.PROCESS, "EXPLICIT_REMEMBER")


def test_a_hypothetical_life_event_is_rejected_not_protected() -> None:
    [unit] = (
        _gate().assess(_content(("Suppose we moved to Mars next year.", True))).assessment.units
    )
    assert (unit.outcome, unit.reason_code, unit.protection) == (
        RelevanceOutcome.REJECT,
        "HYPOTHETICAL",
        None,
    )


def test_the_most_frequent_reason_explains_a_rejected_source() -> None:
    assessment = _gate().assess(_content(("Thanks! Good morning! Is it raining?", True))).assessment
    assert (assessment.outcome, assessment.reason_code) == (RelevanceOutcome.REJECT, "SMALL_TALK")


def test_a_deferred_unit_defers_the_source() -> None:
    assessment = _gate().assess(_content(("Tom likes jazz.", True))).assessment
    assert (assessment.outcome, assessment.reason_code) == (
        RelevanceOutcome.DEFER,
        "AMBIGUOUS_RELEVANCE",
    )


def test_thresholds_are_configurable() -> None:
    strict = _gate(process_threshold=0.95, defer_threshold=0.9)
    assert strict.assess(_content(("I work at the hospital.", True))).assessment.outcome is (
        RelevanceOutcome.REJECT
    )


class _Broken:
    version = "broken-0"

    def analyze(self, text: str) -> Sequence[Sentence]:
        raise RuntimeError("synthetic NLP failure")


def test_an_analyzer_failure_defers_the_source() -> None:
    assessment = _gate(_Broken()).assess(_content(("I prefer tea.", True))).assessment
    assert (assessment.outcome, assessment.reason_code, assessment.units) == (
        RelevanceOutcome.DEFER,
        ANALYSIS_UNAVAILABLE,
        (),
    )


def test_a_source_without_user_turns_is_rejected() -> None:
    assessment = _gate().assess(_content(("Hello, how can I help?", False))).assessment
    assert (assessment.outcome, assessment.reason_code) == (
        RelevanceOutcome.REJECT,
        NO_USER_CONTENT,
    )


# --- the gated pipeline ---------------------------------------------------------------


class _Downstream:
    def __init__(self) -> None:
        self.selected: list[SelectedSentence] = []

    def extract(
        self, content: SourceContent, selected: Sequence[SelectedSentence]
    ) -> PipelineResult:
        self.selected = list(selected)
        return PipelineResult(status=SourceProcessingStatus.EXTRACTED)


@pytest.mark.parametrize(
    ("text", "status", "reason"),
    [
        ("Thanks!", SourceProcessingStatus.REJECTED, "SMALL_TALK"),
        ("Tom likes jazz.", SourceProcessingStatus.DEFERRED, "AMBIGUOUS_RELEVANCE"),
        ("I prefer tea.", SourceProcessingStatus.EXTRACTED, None),
    ],
)
def test_the_pipeline_stops_at_the_gate_or_passes_the_selected_sentences(
    text: str, status: SourceProcessingStatus, reason: str | None
) -> None:
    downstream = _Downstream()
    content = _content((text, True))
    result = GatedPipeline(_gate(), downstream).run(content)
    assert (result.status, result.reason_code) == (status, reason)
    assert result.relevance is not None and result.relevance.source_id == content.source.id
    assert len(downstream.selected) == (1 if status is SourceProcessingStatus.EXTRACTED else 0)


# --- records and settings ---------------------------------------------------------------


def _unit(**values: Any) -> UnitAssessment:
    base: dict[str, Any] = {"segment": 0, "sentence": 0, "outcome": RelevanceOutcome.PROCESS}
    return UnitAssessment(**base | values)


@pytest.mark.parametrize(
    "values",
    [
        {"segment": -1},
        {"outcome": RelevanceOutcome.PROCESS, "reason_code": "WHY"},
        {"outcome": RelevanceOutcome.REJECT},
        {"outcome": RelevanceOutcome.DEFER, "reason_code": "not a code"},
        {"protection": "lower"},
        {"score": 1.5},
        {"signals": {"Bad Name": 0.5}},
        {"signals": {"personal": -0.1}},
        {"signals": {"personal": float("nan")}},
    ],
)
def test_unit_invariants(values: dict[str, Any]) -> None:
    with pytest.raises(DomainValidationError):
        _unit(**values)


def test_a_unit_round_trips_through_json_without_text() -> None:
    unit = _unit(score=0.8, signals={"personal": 1.0}, protection="CORRECTION")
    data = unit.to_json()
    assert UnitAssessment.from_json(data) == unit
    assert set(data) == {
        "segment",
        "sentence",
        "outcome",
        "reason_code",
        "score",
        "signals",
        "protection",
    }


def _assessment(**values: Any) -> RelevanceAssessment:
    base: dict[str, Any] = {
        "id": uuid.uuid4(),
        "owner_id": uuid.uuid4(),
        "source_id": uuid.uuid4(),
        "outcome": RelevanceOutcome.PROCESS,
        "method": METHOD,
        "method_version": "1",
        "assessed_at": T0,
        "units": [_unit()],
    }
    return RelevanceAssessment(**base | values)


@pytest.mark.parametrize(
    "values",
    [
        {"reason_code": "WHY"},
        {"outcome": RelevanceOutcome.REJECT},
        {"outcome": RelevanceOutcome.REJECT, "reason_code": "SMALL_TALK"},  # has a process unit
        {"units": []},  # processed with no processed unit
        {"method": " "},
        {"assessed_at": datetime(2026, 11, 12, 9, 0)},
        {"units": [_unit(), _unit()]},  # the same sentence twice
    ],
)
def test_assessment_invariants(values: dict[str, Any]) -> None:
    with pytest.raises(DomainValidationError):
        _assessment(**values)


def test_processed_units_are_exposed() -> None:
    rejected = _unit(sentence=1, outcome=RelevanceOutcome.REJECT, reason_code="SMALL_TALK")
    assert _assessment(units=[_unit(), rejected]).processed == (_unit(),)


@pytest.mark.parametrize(
    "values",
    [
        {"defer_threshold": 0.6, "process_threshold": 0.5},
        {
            "weight_personal": 0,
            "weight_utility": 0,
            "weight_temporal": 0,
            "weight_context": 0,
            "weight_density": 0,
        },
    ],
)
def test_relevance_settings_are_validated(values: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        RelevanceSettings(**values)


def test_the_user_as_object_counts_as_personal() -> None:
    [unit] = _gate().assess(_content(("It reminds me of home.", True))).assessment.units
    assert unit.signals["personal"] == 0.6


def test_a_short_personal_fragment_is_rejected_as_low_information() -> None:
    [unit] = _gate().assess(_content(("Call me.", True))).assessment.units
    assert (unit.outcome, unit.reason_code) == (RelevanceOutcome.REJECT, "LOW_INFORMATION")
