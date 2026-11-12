"""Phase 8.4 step 3: atomic fact extraction (6.2.3), real spaCy analyzer, no I/O."""

import uuid
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any

import pytest
from pydantic import ValidationError

from memory_engine.config.settings import FactExtractionSettings, RelevanceSettings
from memory_engine.domain.errors import DomainValidationError
from memory_engine.domain.vocabulary import (
    FactModality,
    IngestionPriority,
    InstructionType,
    ProposalStatus,
    SourceProcessingStatus,
    SourceType,
)
from memory_engine.infrastructure.nlp import SpacySentenceAnalyzer
from memory_engine.personal.application.analysis import Sentence, Token
from memory_engine.personal.application.extraction import (
    PipelineResult,
    Segment,
    SourceContent,
)
from memory_engine.personal.application.facts import (
    LONG_SENTENCE,
    LOW_EXTRACTION_CONFIDENCE,
    NO_SUBJECT,
    NO_VERB,
    FactExtraction,
    FactExtractionStage,
    FactExtractor,
)
from memory_engine.personal.application.relevance import (
    RelevanceGate,
    RelevancePolicy,
)
from memory_engine.personal.domain import FactProposal, MemorySource

T0 = datetime(2026, 11, 12, 9, 0, tzinfo=UTC)
ANALYZER = SpacySentenceAnalyzer()
GATE = RelevanceGate(ANALYZER, RelevancePolicy.from_settings(RelevanceSettings()), clock=lambda: T0)


def _content(*segments: Segment) -> SourceContent:
    source = MemorySource(
        id=uuid.uuid4(),
        owner_id=uuid.uuid4(),
        source_type=SourceType.CONVERSATION if len(segments) > 1 else SourceType.TEXT,
        processing_status=SourceProcessingStatus.QUEUED,
        received_at=T0,
        content_sha256="a" * 64,
        instruction_type=InstructionType.REMEMBER,
        priority=IngestionPriority.HIGH,
    )
    return SourceContent(source=source, segments=list(segments))


def _extract(text: str, **settings: Any) -> FactExtraction:
    content = _content(Segment(position=0, text=text))
    return FactExtractor(FactExtractionSettings(**settings)).extract(
        content, GATE.assess(content).selected
    )


def test_proposals_belong_to_the_source_and_locate_their_sentence() -> None:
    content = _content(
        Segment(position=0, text="Hello.", from_user=False),
        Segment(
            position=1, text="Hi! I prefer tea.", speaker="Sam", sent_at="2026-11-01T10:00:00+00:00"
        ),
    )
    extraction = FactExtractor(FactExtractionSettings()).extract(
        content, GATE.assess(content).selected
    )
    proposals = [p for p in extraction.proposals if p.predicate == "prefer"]
    [proposal] = proposals
    assert (proposal.owner_id, proposal.source_id) == (content.source.owner_id, content.source.id)
    assert (proposal.segment, proposal.sentence) == (1, 1)
    assert proposal.original_text == "I prefer tea."
    assert proposal.speaker == "Sam"
    assert proposal.temporal_reference == "2026-11-01T10:00:00+00:00"  # the message's own time
    assert (proposal.method, proposal.method_version) == ("dependency_rules", "1")


def test_a_correction_is_flagged_for_resolution() -> None:
    [first, *_] = _extract("Actually, I said June earlier, but it was July.").proposals
    assert first.correction is True


def test_a_fragment_without_subject_or_verb_needs_review() -> None:
    [proposal] = _extract("Leeds, since last year.").proposals
    assert set(proposal.weaknesses) == {NO_SUBJECT, NO_VERB}
    assert proposal.extraction_confidence == pytest.approx(0.2)
    assert (proposal.status, proposal.reason_code) == (
        ProposalStatus.NEEDS_REVIEW,
        LOW_EXTRACTION_CONFIDENCE,
    )


def test_stricter_thresholds_reject_weak_proposals() -> None:
    [proposal] = _extract("Leeds, since last year.", reject_threshold=0.3).proposals
    assert (proposal.status, proposal.reason_code) == (
        ProposalStatus.REJECTED,
        LOW_EXTRACTION_CONFIDENCE,
    )


def test_a_long_sentence_costs_confidence() -> None:
    text = (
        "I have been working on the same open source project with a small group of friends "
        "from university for nearly four years now, mostly on weekends and late evenings."
    )
    proposals = _extract(text, long_sentence_tokens=10).proposals
    assert all(LONG_SENTENCE in p.weaknesses for p in proposals)
    assert all(p.extraction_confidence <= 0.9 for p in proposals)


class _ExplodingTokens(list[Token]):
    def __iter__(self) -> Any:
        raise RuntimeError("synthetic parse failure")


def test_a_failing_sentence_keeps_the_others() -> None:
    content = _content(Segment(position=0, text="I prefer tea. I like jazz."))
    selected = list(GATE.assess(content).selected)
    broken = replace(
        selected[0],
        sentence=Sentence(index=0, text="I prefer tea.", tokens=_ExplodingTokens()),
    )
    extraction = FactExtractor(FactExtractionSettings()).extract(content, [broken, selected[1]])
    assert list(extraction.failed) == [(0, 0)]
    assert extraction.partial
    assert [p.predicate for p in extraction.proposals] == ["like"]


def test_an_empty_result_is_not_a_failure() -> None:
    extraction = _extract("Should I learn Kotlin?")
    assert (list(extraction.proposals), list(extraction.failed)) == ([], [])
    assert extraction.skipped_questions == 1 and not extraction.partial


# --- the stage ------------------------------------------------------------------------


class _Evaluate:
    def __init__(self) -> None:
        self.seen: FactExtraction | None = None

    def evaluate(self, content: SourceContent, extraction: FactExtraction) -> PipelineResult:
        self.seen = extraction
        return PipelineResult(status=SourceProcessingStatus.EXTRACTED)


def test_the_stage_hands_proposals_to_evaluation() -> None:
    content = _content(Segment(position=0, text="I prefer tea."))
    downstream = _Evaluate()
    result = FactExtractionStage(FactExtractor(FactExtractionSettings()), downstream).extract(
        content, GATE.assess(content).selected
    )
    assert result.status is SourceProcessingStatus.EXTRACTED
    assert downstream.seen is not None and len(downstream.seen.proposals) == 1


# --- records and settings ---------------------------------------------------------------


def _proposal(**values: Any) -> FactProposal:
    base: dict[str, Any] = {
        "id": uuid.uuid4(),
        "owner_id": uuid.uuid4(),
        "source_id": uuid.uuid4(),
        "segment": 0,
        "sentence": 0,
        "original_text": "I prefer tea.",
        "proposition": "The user prefers tea.",
        "modality": FactModality.FACTUAL,
        "speaker": "user",
        "extraction_confidence": 1.0,
        "status": ProposalStatus.EXTRACTED,
        "method": "dependency_rules",
        "method_version": "1",
    }
    return FactProposal(**base | values)


@pytest.mark.parametrize(
    "values",
    [
        {"segment": -1},
        {"proposition": " "},
        {"extraction_confidence": 1.2},
        {"extraction_confidence": float("nan")},
        {"status": ProposalStatus.NEEDS_REVIEW},
        {"reason_code": "WHY"},
        {"status": ProposalStatus.REJECTED, "reason_code": "lower"},
        {"unresolved_references": ("it",)},
        {"conditions": ("if it rains",)},
        {"weaknesses": ("bad code",)},
    ],
)
def test_proposal_invariants(values: dict[str, Any]) -> None:
    with pytest.raises(DomainValidationError):
        _proposal(**values)


def test_the_stored_structure_has_no_evidence_text() -> None:
    structure = _proposal(subject="the user", predicate="prefer", object="tea").structure()
    assert structure["subject"] == "the user" and structure["modality"] == "factual"
    assert "original_text" not in structure and "proposition" not in structure


def test_fact_settings_are_validated() -> None:
    with pytest.raises(ValidationError):
        FactExtractionSettings(review_threshold=0.2, reject_threshold=0.5)


@pytest.mark.parametrize(
    ("text", "modality", "proposition"),
    [
        (
            "I would like to visit Japan.",
            FactModality.INTENDED,
            "The user would like to visit Japan.",
        ),
        ("I would probably say no.", FactModality.POSSIBLE, None),
        ("I study Spanish every day.", FactModality.FACTUAL, "The user studies Spanish every day."),
    ],
)
def test_modality_and_agreement(text: str, modality: FactModality, proposition: str | None) -> None:
    [proposal] = _extract(text).proposals
    assert proposal.modality is modality
    if proposition is not None:
        assert proposal.proposition == proposition
