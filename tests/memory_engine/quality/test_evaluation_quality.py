"""Quality: evaluation and origin classification against their dataset (8.4 step 4).

The labels were written from the approved rule tables BEFORE the evaluator
existed. Every sentence is selected (the gate is bypassed) so only 6.2.4-6.2.5
are measured, on top of fact extraction. A case matches when the number of
proposals and every labelled field match. ``uncertainty`` lists codes that
must be present. The bar is an uncalibrated accuracy floor.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from tests.memory_engine.quality.datasets import Case, load_dataset

from memory_engine.config.settings import EvaluationSettings, FactExtractionSettings
from memory_engine.domain.vocabulary import (
    IngestionPriority,
    InstructionType,
    RelevanceOutcome,
    SourceProcessingStatus,
    SourceType,
)
from memory_engine.infrastructure.nlp import SpacySentenceAnalyzer
from memory_engine.personal.application.evaluation import ProposalEvaluator
from memory_engine.personal.application.extraction import Segment, SourceContent
from memory_engine.personal.application.facts import FactExtractor
from memory_engine.personal.application.relevance import SelectedSentence
from memory_engine.personal.domain import EvaluatedProposal, MemorySource, UnitAssessment

T0 = datetime(2026, 11, 12, 9, 0, tzinfo=UTC)
CASES = load_dataset("evaluation", 1)
MIN_ACCURACY = 0.85
ANALYZER = SpacySentenceAnalyzer()
EXTRACTOR = FactExtractor(FactExtractionSettings())
EVALUATOR = ProposalEvaluator(EvaluationSettings())


def evaluated(case: Case) -> list[EvaluatedProposal]:
    instruction = InstructionType(case.input["instruction"])
    source = MemorySource(
        id=uuid.uuid4(),
        owner_id=uuid.uuid4(),
        source_type=SourceType.TEXT,
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
    segment = Segment(position=0, text=case.input["text"])
    content = SourceContent(source=source, segments=[segment])
    selected = [
        SelectedSentence(
            segment=segment,
            sentence=sentence,
            unit=UnitAssessment(
                segment=0, sentence=sentence.index, outcome=RelevanceOutcome.PROCESS
            ),
        )
        for sentence in ANALYZER.analyze(segment.text)
    ]
    proposals = EXTRACTOR.extract(content, selected).proposals
    return EVALUATOR.evaluate(content, proposals)


def _mismatches(expected: dict[str, Any], item: EvaluatedProposal) -> list[str]:
    evaluation, classification = item.evaluation, item.classification
    actual: dict[str, Any] = {
        "category": evaluation.category,
        "importance": evaluation.importance,
        "fact_confidence": evaluation.fact_confidence,
        "freshness": evaluation.freshness.value,
        "origin": classification.origin.value,
        "outcome": item.outcome.value,
        "classification_reason": classification.reason_code,
    }
    problems = [
        f"{key}: expected {value!r}, got {actual[key]!r}"
        for key, value in expected.items()
        if key != "uncertainty" and actual[key] != value
    ]
    missing = set(expected.get("uncertainty", [])) - set(evaluation.uncertainty)
    if missing:
        problems.append(f"uncertainty lacks {sorted(missing)}")
    return problems


def evaluate_case(case: Case) -> list[str]:
    expected = case.expected["proposals"]
    items = evaluated(case)
    if len(items) != len(expected):
        return [f"expected {len(expected)} proposals, got {len(items)}"]
    return [p for e, got in zip(expected, items, strict=True) for p in _mismatches(e, got)]


def test_overall_evaluation_accuracy() -> None:
    misses = {case.id: problems for case in CASES if (problems := evaluate_case(case))}
    accuracy = 1 - len(misses) / len(CASES)
    assert accuracy >= MIN_ACCURACY, misses


@pytest.mark.parametrize(
    "case_id",
    # Evidence-aware rules from 6.2.4 section 6.5 and 6.2.5 rules 4-5 must always hold.
    ["eval-006", "eval-009", "eval-010", "eval-011", "eval-012", "eval-020", "eval-021"],
)
def test_evidence_rules_hold_exactly(case_id: str) -> None:
    case = next(c for c in CASES if c.id == case_id)
    assert evaluate_case(case) == [], case.notes


def test_dimensions_are_independent() -> None:
    # Importance and fact confidence move separately (6.2.4 AC-02, AC-03).
    items = [item for case in CASES for item in evaluated(case)]
    pairs = {(i.evaluation.importance, i.evaluation.fact_confidence) for i in items}
    assert len({p[0] for p in pairs}) > 3 and len({p[1] for p in pairs}) > 3
    assert all(i.evaluation.observed_at == T0.isoformat() for i in items)  # never invented
