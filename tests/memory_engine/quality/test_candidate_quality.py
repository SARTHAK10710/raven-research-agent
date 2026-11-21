"""Quality: candidate generation (6.2.6) against its dataset (8.4 step 5).

The labels were written from the approved category rules BEFORE the
generator existed, by the same author who then wrote it; the eight examples
of 6.2.6 section 8.4 are taken from the specification. The first run matched
21 of 22; cand-019 ("working on a mobile app") then led to one rule change
(project-like words are also looked for in prepositional attributes), so
that case is no longer an independent measure. Every sentence is
selected (the gate is bypassed) and fact extraction and evaluation run for
real, so a case measures the whole path into candidates. A case matches when
the number of candidates and each candidate's categories and status match.
The bar is an uncalibrated accuracy floor; the specification's own examples
must hold exactly.
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
from memory_engine.personal.application.candidates import CandidateGenerator
from memory_engine.personal.application.evaluation import ProposalEvaluator
from memory_engine.personal.application.extraction import (
    PipelineResult,
    Segment,
    SourceContent,
)
from memory_engine.personal.application.facts import FactExtractor
from memory_engine.personal.application.relevance import SelectedSentence
from memory_engine.personal.domain import MemorySource, UnitAssessment

T0 = datetime(2026, 11, 22, 9, 0, tzinfo=UTC)
CASES = load_dataset("candidates", 1)
MIN_ACCURACY = 0.85
ANALYZER = SpacySentenceAnalyzer()
EXTRACTOR = FactExtractor(FactExtractionSettings())
EVALUATOR = ProposalEvaluator(EvaluationSettings())
GENERATOR = CandidateGenerator(clock=lambda: T0)


def generated(case: Case) -> PipelineResult:
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
    extraction = EXTRACTOR.extract(content, selected)
    return GENERATOR.generate(
        content, extraction, EVALUATOR.evaluate(content, extraction.proposals)
    )


def evaluate_case(case: Case) -> list[str]:
    expected: list[dict[str, Any]] = case.expected["candidates"]
    result = generated(case)
    final = {e.candidate_id: e.to_status.value for e in result.evaluations}
    actual = [
        {"categories": [c.value for c in candidate.categories], "status": final[candidate.id]}
        for candidate in result.candidates
    ]
    if len(actual) != len(expected):
        return [f"expected {len(expected)} candidates, got {actual}"]
    return [
        f"expected {want}, got {got}"
        for want, got in zip(expected, actual, strict=True)
        if want != got
    ]


def test_overall_candidate_accuracy() -> None:
    misses = {case.id: problems for case in CASES if (problems := evaluate_case(case))}
    accuracy = 1 - len(misses) / len(CASES)
    assert accuracy >= MIN_ACCURACY, misses


@pytest.mark.parametrize("case_id", [f"cand-00{n}" for n in range(1, 9)])
def test_the_specification_examples_hold_exactly(case_id: str) -> None:
    case = next(c for c in CASES if c.id == case_id)
    assert evaluate_case(case) == [], case.notes


@pytest.mark.parametrize("case_id", ["cand-009", "cand-010"])
def test_several_categories_can_apply(case_id: str) -> None:
    # 6.2.6 AC-04.
    case = next(c for c in CASES if c.id == case_id)
    assert evaluate_case(case) == [], case.notes


def test_every_candidate_keeps_independent_scores_and_provenance() -> None:
    for case in CASES:
        result = generated(case)
        assert result.outcome_summary is not None
        assert result.outcome_summary["candidates"] == len(result.candidates)
        for candidate in result.candidates:
            # 6.2.6 AC-05, AC-06, AC-08, AC-09.
            assert candidate.importance is not None and candidate.confidence is not None
            assert candidate.extraction_confidence is not None
            assert candidate.extraction_metadata["location"]["segment"] == 0
            assert candidate.temporal["reference_time"] == T0.isoformat()
            assert candidate.evaluation_metadata["origin"]["evidence"]
