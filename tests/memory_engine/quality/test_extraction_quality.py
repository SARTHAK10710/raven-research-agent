"""Quality: atomic fact extraction against its synthetic dataset (8.4 step 3; 6.2.3).

Each case is a single remember-instructed text, so the relevance gate passes
every sentence and only extraction is measured. Labels say what a careful
reviewer expects; a case matches when the number of proposals and every
labelled field of every proposal match. ``contains`` lists substrings of the
proposition. The bar is an uncalibrated accuracy floor (step 6 sets the
quality thresholds).
"""

import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from tests.memory_engine.quality.datasets import Case, load_dataset

from memory_engine.config.settings import FactExtractionSettings, RelevanceSettings
from memory_engine.domain.vocabulary import (
    IngestionPriority,
    InstructionType,
    SourceProcessingStatus,
    SourceType,
)
from memory_engine.infrastructure.nlp import SpacySentenceAnalyzer
from memory_engine.personal.application.extraction import Segment, SourceContent
from memory_engine.personal.application.facts import FactExtractor
from memory_engine.personal.application.relevance import RelevanceGate, RelevancePolicy
from memory_engine.personal.domain import FactProposal, MemorySource

T0 = datetime(2026, 11, 12, 9, 0, tzinfo=UTC)
CASES = load_dataset("extraction", 1)
MIN_ACCURACY = 0.85
GATE = RelevanceGate(
    SpacySentenceAnalyzer(), RelevancePolicy.from_settings(RelevanceSettings()), clock=lambda: T0
)
EXTRACTOR = FactExtractor(FactExtractionSettings())


def proposals_for(case: Case) -> list[FactProposal]:
    source = MemorySource(
        id=uuid.uuid4(),
        owner_id=uuid.uuid4(),
        source_type=SourceType.TEXT,
        processing_status=SourceProcessingStatus.QUEUED,
        received_at=T0,
        content_sha256="a" * 64,
        instruction_type=InstructionType(case.input["instruction"]),
        priority=IngestionPriority.HIGH,
    )
    content = SourceContent(source=source, segments=[Segment(position=0, text=case.input["text"])])
    return list(EXTRACTOR.extract(content, GATE.assess(content).selected).proposals)


def _mismatches(expected: dict[str, Any], proposal: FactProposal) -> list[str]:
    actual = {
        "subject": proposal.subject,
        "predicate": proposal.predicate,
        "object": proposal.object,
        "modality": proposal.modality.value,
        "negated": proposal.negated,
        "status": proposal.status.value,
        "temporal": list(proposal.temporal),
        "quantities": list(proposal.quantities),
        "attributed_to": proposal.attributed_to,
        "conditions": len(proposal.conditions),
        "unresolved": list(proposal.unresolved_references),
    }
    problems = [
        f"{key}: expected {value!r}, got {actual[key]!r}"
        for key, value in expected.items()
        if key != "contains" and actual[key] != value
    ]
    problems += [
        f"proposition lacks {text!r}"
        for text in expected.get("contains", [])
        if text not in proposal.proposition
    ]
    return problems


def _evaluate(case: Case) -> list[str]:
    expected = case.expected["proposals"]
    proposals = proposals_for(case)
    if len(proposals) != len(expected):
        return [f"expected {len(expected)} proposals, got {len(proposals)}"]
    return [p for e, got in zip(expected, proposals, strict=True) for p in _mismatches(e, got)]


def test_overall_extraction_accuracy() -> None:
    misses = {case.id: problems for case in CASES if (problems := _evaluate(case))}
    accuracy = 1 - len(misses) / len(CASES)
    assert accuracy >= MIN_ACCURACY, misses


@pytest.mark.parametrize(
    "case_id",
    # The 6.2.3 acceptance examples must always hold exactly.
    ["ext-001", "ext-002", "ext-003", "ext-004", "ext-005", "ext-006", "ext-009", "ext-022"],
)
def test_specification_examples_hold_exactly(case_id: str) -> None:
    case = next(c for c in CASES if c.id == case_id)
    assert _evaluate(case) == [], case.notes


def test_every_proposal_carries_its_evidence() -> None:
    for case in CASES:
        for proposal in proposals_for(case):
            assert proposal.original_text == case.input["text"]  # AC-05, AC-15
            assert proposal.temporal_reference == T0.isoformat()  # AC-11
            assert proposal.speaker == "user"
