"""Phase 8.5 step 1: entity identification and classification, with a fake analyzer."""

import uuid
from collections.abc import Sequence
from typing import Any

import pytest

from memory_engine.domain.errors import DomainValidationError
from memory_engine.domain.vocabulary import CandidateOrigin, CandidateStatus, EntityType
from memory_engine.personal.application.analysis import Sentence, Token
from memory_engine.personal.application.identification import EntityIdentifier
from memory_engine.personal.domain import IdentifiedMention, MemoryCandidate, TypeBasis

OWNER = uuid.uuid4()
SOURCE = uuid.uuid4()


def tok(
    text: str,
    pos: str,
    dep: str,
    head: int,
    entity: str = "",
    lemma: str | None = None,
    ws: str = " ",
) -> Token:
    return Token(
        text=text,
        lower=text.lower(),
        lemma=lemma or text.lower(),
        pos=pos,
        dep=dep,
        head=head,
        entity=entity,
        whitespace=ws,
    )


def sentence(*tokens: Token, index: int = 0) -> Sentence:
    text = "".join(t.text + t.whitespace for t in tokens).rstrip()
    return Sentence(index=index, text=text, tokens=tokens)


class FakeAnalyzer:
    version = "fake-1"

    def __init__(self, *sentences: Sentence) -> None:
        self._sentences = sentences

    def analyze(self, text: str) -> Sequence[Sentence]:
        return self._sentences


def candidate(proposition: str, **values: Any) -> MemoryCandidate:
    base: dict[str, Any] = {
        "id": uuid.uuid4(),
        "owner_id": OWNER,
        "source_id": SOURCE,
        "proposition": proposition,
        "status": CandidateStatus.VALIDATED,
        "origin": CandidateOrigin.EXPLICIT,
        "extraction_metadata": {"location": {"segment": 2, "sentence": 1}},
    }
    return MemoryCandidate(**base | values)


def identify(*sentences: Sentence, **values: Any) -> list[IdentifiedMention]:
    proposition = " ".join(s.text for s in sentences)
    return EntityIdentifier(FakeAnalyzer(*sentences)).identify(candidate(proposition, **values))


WORKS_AT = sentence(
    tok("The", "DET", "det", 1),
    tok("user", "NOUN", "nsubj", 2),
    tok("works", "VERB", "ROOT", 2, lemma="work"),
    tok("at", "ADP", "prep", 2),
    tok("Stripe", "PROPN", "pobj", 3, entity="ORG", ws=""),
    tok(".", "PUNCT", "punct", 2, ws=""),
)
USES = sentence(
    tok("The", "DET", "det", 1),
    tok("user", "NOUN", "nsubj", 2),
    tok("uses", "VERB", "ROOT", 2, lemma="use"),
    tok("Python", "PROPN", "dobj", 2),
    tok("and", "CCONJ", "cc", 3),
    tok("Docker", "PROPN", "conj", 3, entity="PERSON", ws=""),
    tok(".", "PUNCT", "punct", 2, ws=""),
)
GRADUATED = sentence(
    tok("The", "DET", "det", 1),
    tok("user", "NOUN", "nsubj", 2),
    tok("graduated", "VERB", "ROOT", 2, lemma="graduate"),
    tok("from", "ADP", "prep", 2),
    tok("the", "DET", "det", 5, entity="ORG"),
    tok("University", "PROPN", "pobj", 3, entity="ORG"),
    tok("of", "ADP", "prep", 5, entity="ORG"),
    tok("Leeds", "PROPN", "pobj", 6, entity="ORG"),
    tok("in", "ADP", "prep", 2),
    tok("2019", "NUM", "pobj", 8, entity="DATE", ws=""),
    tok(".", "PUNCT", "punct", 2, ws=""),
)
MANAGER = sentence(
    tok("The", "DET", "det", 1),
    tok("user", "NOUN", "poss", 3, ws=""),
    tok("'s", "PART", "case", 1),
    tok("manager", "NOUN", "compound", 5),
    tok("Priya", "PROPN", "compound", 5, entity="PERSON"),
    tok("Shah", "PROPN", "nsubj", 6, entity="PERSON"),
    tok("reports", "VERB", "ROOT", 6, lemma="report"),
    tok("to", "ADP", "prep", 6),
    tok("the", "DET", "det", 9),
    tok("CTO", "PROPN", "pobj", 7, entity="ORG"),
    tok("on", "ADP", "prep", 6),
    tok("Monday", "PROPN", "pobj", 10, entity="DATE", ws=""),
    tok(".", "PUNCT", "punct", 6, ws=""),
)
PREFERS = sentence(
    tok("The", "DET", "det", 1),
    tok("user", "NOUN", "nsubj", 2),
    tok("prefers", "VERB", "ROOT", 2, lemma="prefer"),
    tok("the", "DET", "det", 4),
    tok("iPhone", "PROPN", "dobj", 2),
    tok("15", "NUM", "nummod", 4, entity="CARDINAL", ws=""),
    tok(".", "PUNCT", "punct", 2, ws=""),
)


def _summary(mentions: list[IdentifiedMention]) -> list[tuple[str, str, str]]:
    return [(m.name, m.entity_type.value, m.basis.value) for m in mentions]


def test_a_context_rule_types_the_name_and_ner_agreement_is_recorded() -> None:
    [mention] = identify(WORKS_AT)
    assert (mention.name, mention.entity_type, mention.rule) == (
        "Stripe",
        EntityType.ORGANIZATION,
        "work_at",
    )
    assert (mention.ner_label, mention.ner_agrees) == ("ORG", True)
    assert (mention.segment, mention.sentence) == (2, 1)  # the evidence location
    assert (mention.owner_id, mention.source_id) == (OWNER, SOURCE)
    assert mention.method_version == "1+fake-1"


def test_context_wins_over_a_disagreeing_ner_label_and_reaches_conjuncts() -> None:
    mentions = identify(USES)
    assert _summary(mentions) == [
        ("Python", "technology", "context_rule"),
        ("Docker", "technology", "context_rule"),
    ]
    assert (mentions[1].ner_label, mentions[1].ner_agrees) == ("PERSON", False)


def test_of_joins_a_name_and_dates_are_never_names() -> None:
    [mention] = identify(GRADUATED)
    assert (mention.name, mention.entity_type, mention.rule) == (
        "University of Leeds",
        EntityType.INSTITUTION,
        "graduate_from",
    )


def test_a_named_relation_is_a_person_and_titles_and_days_are_not_names() -> None:
    assert _summary(identify(MANAGER)) == [("Priya Shah", "person", "relation_noun")]


def test_without_evidence_the_type_stays_unknown_and_a_number_completes_the_name() -> None:
    [mention] = identify(PREFERS)
    assert (mention.name, mention.entity_type, mention.basis) == (
        "iPhone 15",
        EntityType.UNKNOWN,
        TypeBasis.NONE,
    )
    assert mention.ner_label is None  # CARDINAL belongs to the number, not the name


def test_offsets_point_into_the_proposition_across_sentences() -> None:
    second = sentence(*USES.tokens, index=1)
    proposition = f"{WORKS_AT.text} {second.text}"
    mentions = EntityIdentifier(FakeAnalyzer(WORKS_AT, second)).identify(candidate(proposition))
    assert [proposition[m.start : m.end] for m in mentions] == ["Stripe", "Python", "Docker"]


@pytest.mark.parametrize(
    "status",
    [CandidateStatus.NEEDS_REVIEW, CandidateStatus.CANDIDATE, CandidateStatus.REJECTED],
)
def test_only_validated_candidates_are_read(status: CandidateStatus) -> None:
    assert identify(WORKS_AT, status=status) == []


def test_a_keyword_refines_a_destination_and_a_context_type() -> None:
    school = sentence(
        tok("The", "DET", "det", 1),
        tok("daughter", "NOUN", "nsubj", 2),
        tok("goes", "VERB", "ROOT", 2, lemma="go"),
        tok("to", "ADP", "prep", 2),
        tok("Riverside", "PROPN", "compound", 5),
        tok("School", "PROPN", "pobj", 3, ws=""),
        tok(".", "PUNCT", "punct", 2, ws=""),
    )
    assert _summary(identify(school)) == [("Riverside School", "institution", "name_keyword")]


def _mention(**values: Any) -> IdentifiedMention:
    base: dict[str, Any] = {
        "owner_id": OWNER,
        "source_id": SOURCE,
        "candidate_id": uuid.uuid4(),
        "name": "Stripe",
        "entity_type": EntityType.ORGANIZATION,
        "basis": TypeBasis.CONTEXT_RULE,
        "rule": "work_at",
        "start": 18,
        "end": 24,
        "segment": 0,
        "sentence": 0,
        "method": "entity_rules",
        "method_version": "1",
    }
    return IdentifiedMention(**base | values)


@pytest.mark.parametrize(
    "values",
    [
        {"name": " Stripe"},
        {"name": ""},
        {"end": 23},
        {"start": -1, "end": 5},
        {"segment": -1},
        {"entity_type": EntityType.UNKNOWN},
        {"basis": TypeBasis.NONE, "rule": None},
        {"basis": TypeBasis.NAME_KEYWORD},
        {"rule": "Work At"},
        {"ner_label": "org"},
        {"ner_agrees": True},
        {"method": " "},
    ],
)
def test_mention_invariants(values: dict[str, Any]) -> None:
    with pytest.raises(DomainValidationError):
        _mention(**values)


def test_a_valid_unknown_mention() -> None:
    mention = _mention(entity_type=EntityType.UNKNOWN, basis=TypeBasis.NONE, rule=None)
    assert mention.entity_type is EntityType.UNKNOWN
