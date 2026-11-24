"""Quality: entity identification and classification against its dataset (8.5 step 1).

Labels: drafted by the author of the rules, then reviewed and approved by the
project owner on 2026-11-24 BEFORE the identifier ran against them (owner
decision, 7.1 section 26.5). Each case runs fact extraction, evaluation and
candidate generation for real (the gate is bypassed, as in the 8.4 component
sets), then identifies entities in the validated candidates.

A case matches when the set of (name, type) pairs equals the labelled set;
names compare case-insensitively without a leading article. The bar is the
established uncalibrated 0.85 case-accuracy floor (7.1 section 25.10).
Mention-level precision and recall are reported in ``score``.

First run (2026-11-24, no rule changed afterwards): 26 of 30 cases match
(accuracy 0.867); mention precision 0.938, recall 0.882. Misses, kept visible:
ent-003 (Raven not found), ent-015 (Sarah typed unknown: "meeting with" did not
match), ent-016 (FastAPI not found), ent-024 (AWS typed unknown: "deploy on" did
not match).
"""

import uuid
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any

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
from memory_engine.personal.application.extraction import Segment, SourceContent
from memory_engine.personal.application.facts import FactExtractor
from memory_engine.personal.application.identification import EntityIdentifier
from memory_engine.personal.application.relevance import SelectedSentence
from memory_engine.personal.domain import MemorySource, UnitAssessment

T0 = datetime(2026, 11, 24, 9, 0, tzinfo=UTC)
CASES = load_dataset("entities", 1)
MIN_ACCURACY = 0.85
ANALYZER = SpacySentenceAnalyzer()
EXTRACTOR = FactExtractor(FactExtractionSettings())
EVALUATOR = ProposalEvaluator(EvaluationSettings())
GENERATOR = CandidateGenerator(clock=lambda: T0)
IDENTIFIER = EntityIdentifier(ANALYZER)
_ARTICLES = ("the ", "a ", "an ")


def _key(name: str) -> str:
    name = name.strip().lower()
    for article in _ARTICLES:
        if name.startswith(article):
            name = name[len(article) :]
    return name


def identified(case: Case) -> set[tuple[str, str]]:
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
    result = GENERATOR.generate(
        content, extraction, EVALUATOR.evaluate(content, extraction.proposals)
    )
    final = {e.candidate_id: e.to_status for e in result.evaluations}
    found: set[tuple[str, str]] = set()
    for candidate in result.candidates:
        stored = replace(candidate, status=final.get(candidate.id, candidate.status))
        found |= {(_key(m.name), m.entity_type.value) for m in IDENTIFIER.identify(stored)}
    return found


def expected(case: Case) -> set[tuple[str, str]]:
    mentions: list[dict[str, Any]] = case.expected["mentions"]
    return {(_key(m["name"]), m["type"]) for m in mentions}


def score() -> dict[str, Any]:
    misses: dict[str, str] = {}
    produced = labelled = matched = 0
    for case in CASES:
        got, want = identified(case), expected(case)
        produced += len(got)
        labelled += len(want)
        matched += len(got & want)
        if got != want:
            misses[case.id] = f"missing {sorted(want - got)}, extra {sorted(got - want)}"
    return {
        "accuracy": 1 - len(misses) / len(CASES),
        "precision": matched / produced if produced else 1.0,
        "recall": matched / labelled if labelled else 1.0,
        "misses": misses,
    }


def test_entity_accuracy_meets_the_floor() -> None:
    result = score()
    assert result["accuracy"] >= MIN_ACCURACY, result
