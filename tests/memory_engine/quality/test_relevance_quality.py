"""Quality: the relevance gate against its synthetic dataset (8.4 step 2; 6.2.2).

Labels are what a careful reviewer would decide, not what the gate outputs.
Two bars, both uncalibrated (step 6 sets the quality thresholds):

- every case whose label names a reason comes from a deterministic rule or a
  clear-cut score, so the outcome AND the reason must match;
- across all cases, the outcome must match in at least ``MIN_ACCURACY``.
"""

import uuid
from datetime import UTC, datetime

import pytest
from tests.memory_engine.quality.datasets import Case, load_dataset

from memory_engine.config.settings import RelevanceSettings
from memory_engine.domain.vocabulary import (
    IngestionPriority,
    InstructionType,
    SourceProcessingStatus,
    SourceType,
)
from memory_engine.infrastructure.nlp import SpacySentenceAnalyzer
from memory_engine.personal.application.extraction import Segment, SourceContent
from memory_engine.personal.application.relevance import RelevanceGate, RelevancePolicy
from memory_engine.personal.domain import MemorySource

T0 = datetime(2026, 11, 12, 9, 0, tzinfo=UTC)
CASES = load_dataset("relevance", 1)
MIN_ACCURACY = 0.85
GATE = RelevanceGate(
    SpacySentenceAnalyzer(), RelevancePolicy.from_settings(RelevanceSettings()), clock=lambda: T0
)


def content_of(case: Case) -> SourceContent:
    instruction = InstructionType(case.input["instruction"])
    owner = uuid.uuid4()
    source = MemorySource(
        id=uuid.uuid4(),
        owner_id=owner,
        source_type=SourceType.CONVERSATION if len(case.input["segments"]) > 1 else SourceType.TEXT,
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
    segments = [
        Segment(position=i, text=s["text"], from_user=s["from_user"])
        for i, s in enumerate(case.input["segments"])
    ]
    return SourceContent(source=source, segments=segments)


def _outcome(case: Case) -> tuple[str, str | None, str | None]:
    assessment = GATE.assess(content_of(case)).assessment
    protections = {u.protection for u in assessment.units if u.protection}
    reason = assessment.reason_code or (sorted(protections)[0] if protections else None)
    return assessment.outcome.value, reason, assessment.reason_code


@pytest.mark.parametrize("case", [c for c in CASES if "reason" in c.expected], ids=lambda c: c.id)
def test_labelled_reasons_match_exactly(case: Case) -> None:
    outcome, reason, _ = _outcome(case)
    assert (outcome, reason) == (case.expected["outcome"], case.expected["reason"]), case.notes


def test_overall_outcome_accuracy() -> None:
    misses = [
        (c.id, c.expected["outcome"], got)
        for c in CASES
        if (got := _outcome(c)[0]) != c.expected["outcome"]
    ]
    accuracy = 1 - len(misses) / len(CASES)
    assert accuracy >= MIN_ACCURACY, misses


def test_the_dataset_covers_every_outcome() -> None:
    outcomes = {c.expected["outcome"] for c in CASES}
    assert outcomes == {"process", "defer", "reject"}
