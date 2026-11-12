"""Atomic fact extraction (6.2.3; owner-approved design, 8.4 step 3).

Input: the sentences the relevance gate selected, already parsed. Output:
:class:`FactProposal` records, in memory, for evaluation (step 4) and
candidate generation (step 5).

**Clauses** (dependency-parse rules). One proposal per clause:

- the sentence root, and verbs coordinated with a clause head (``conj``):
  "I study Kotlin and I want to become a developer" -> two proposals (AC-02);
- a participial clause hanging off a clause head ("..., currently learning
  Kotlin") -> its own proposal, sharing the subject;
- a statement reported with "say/tell/mention/claim" -> a proposal attributed
  to the reporter, never to the user (AC-06, AC-14);
- a clause under "think/believe/guess" by the user -> its own proposal with
  ``possible`` modality; the belief verb itself is not a fact.

Everything else attached to the clause verb (objects, prepositional details,
dates, durations, organizations, frequencies) stays in the same proposal, so
connected attributes keep their shared meaning (AC-03). A condition ("if/
unless/when ...") stays in the proposition and in ``conditions``, and makes
the modality ``conditional`` (AC-08).

**References** (owner decision): first person only. "I/me/myself" become "the
user", "my" becomes "the user's", "we/us" "the user and others", "our" "the
user's". Third-person pronouns are kept as written and listed as unresolved,
and the proposal goes to review (AC-13). Entity resolution is plan 8.5.

**Confidence** (owner decision): 1.0 minus a penalty per weakness (no
subject, no verb, unresolved reference, nothing beyond subject and verb, a very
long sentence). Below the review threshold -> ``needs_review``; below the
reject threshold -> ``rejected``. Uncalibrated (``FactExtractionSettings``).

Questions are never turned into assertions (AC-07). A failure on one sentence
is recorded and does not discard the others (AC-18); an empty result is a
valid outcome, distinct from a failure (AC-19).
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from memory_engine.config.settings import FactExtractionSettings
from memory_engine.domain.identifiers import new_id
from memory_engine.domain.vocabulary import FactModality, ProposalStatus
from memory_engine.personal.application.analysis import Sentence, Token
from memory_engine.personal.application.extraction import (
    PipelineResult,
    Segment,
    SourceContent,
)
from memory_engine.personal.application.relevance import SelectedSentence
from memory_engine.personal.domain import FactProposal

METHOD = "dependency_rules"
METHOD_VERSION = "1"

# Weakness and reason codes.
NO_SUBJECT = "NO_SUBJECT"
NO_VERB = "NO_VERB"
UNRESOLVED_REFERENCE = "UNRESOLVED_REFERENCE"
NO_OBJECT = "NO_OBJECT"
LONG_SENTENCE = "LONG_SENTENCE"
LOW_EXTRACTION_CONFIDENCE = "LOW_EXTRACTION_CONFIDENCE"

_TYPOGRAPHIC_APOSTROPHE = chr(0x2019)
_SUBJECT_DEPS = frozenset({"nsubj", "nsubjpass", "csubj", "expl"})
_OBJECT_DEPS = ("dobj", "attr", "acomp", "oprd", "dative")
_DETAIL_DEPS = frozenset({"prep", "npadvmod", "advmod", "agent", "prt", "dative", "acomp"})
# "when/once" usually state a habit or a time, not a condition, so they are not here.
_CONDITION_MARKS = frozenset({"if", "unless", "provided"})
_REPORTING = frozenset({"say", "tell", "mention", "claim", "report", "write"})
_BELIEF = frozenset({"think", "believe", "guess", "suspect", "reckon", "feel", "expect"})
_INTENT = frozenset({"want", "plan", "intend", "hope", "aim", "wish", "mean"})
_POSSIBLE_AUX = frozenset({"might", "may", "could"})
_FUTURE_AUX = frozenset({"will", "shall", "'ll"})
_HEDGES = frozenset({"maybe", "perhaps", "possibly", "probably"})
_UNRESOLVED = frozenset(
    {"he", "she", "it", "they", "him", "her", "them", "his", "its", "their", "this", "that"}
)
_TEMPORAL_ENTITIES = frozenset({"DATE", "TIME"})
_QUANTITY_ENTITIES = frozenset({"QUANTITY", "CARDINAL", "MONEY", "PERCENT"})
_FIRST_PERSON = {
    "i": "the user",
    "me": "the user",
    "myself": "the user",
    "my": "the user's",
    "mine": "the user's",
    "we": "the user and others",
    "us": "the user and others",
    "ourselves": "the user and others",
    "our": "the user's",
    "ours": "the user's",
}
_THIRD_PERSON_VERB = {"am": "is", "'m": "is", "have": "has", "'ve": "has", "do": "does"}
_CORRECTION = re.compile(
    r"^(actually|correction|to clarify|i meant|i mean|sorry, i meant)\b|"
    r"\b(not anymore|no longer|i was wrong|scratch that)\b"
)


@dataclass(frozen=True, slots=True, kw_only=True)
class FactExtraction:
    """The result of 6.2.3 for one source (6.2.3 section 5.10)."""

    proposals: Sequence[FactProposal]
    failed: Sequence[tuple[int, int]] = ()  # (segment, sentence) that could not be processed
    skipped_questions: int = 0

    @property
    def partial(self) -> bool:
        return bool(self.failed)


class ProposalStage(Protocol):
    """Evaluation and candidate generation (steps 4-5)."""

    def evaluate(self, content: SourceContent, extraction: FactExtraction) -> PipelineResult: ...


@dataclass(frozen=True, slots=True)
class _Clause:
    head: int
    tokens: frozenset[int]
    subject: tuple[int, ...]  # the subject phrase, possibly inherited
    attributed_to: tuple[int, ...] = ()  # the reporter, for reported speech
    believed: bool = False  # under "I think ..."


class _Parse:
    """Index helpers over one analyzed sentence."""

    def __init__(self, sentence: Sentence) -> None:
        self.tokens = list(sentence.tokens)
        self.children: list[list[int]] = [[] for _ in self.tokens]
        for index, token in enumerate(self.tokens):
            if token.head != index and 0 <= token.head < len(self.tokens):
                self.children[token.head].append(index)

    def subtree(self, index: int, stop: frozenset[int] = frozenset()) -> set[int]:
        result = {index}
        for child in self.children[index]:
            if child not in stop:
                result |= self.subtree(child, stop)
        return result

    def child(self, index: int, deps: frozenset[str] | tuple[str, ...]) -> int | None:
        return next((c for c in self.children[index] if self.tokens[c].dep in deps), None)

    def is_verb(self, index: int) -> bool:
        return self.tokens[index].pos in ("VERB", "AUX")


def _render(parse: _Parse, indices: Sequence[int] | set[int] | frozenset[int]) -> str:
    """The tokens' text, in order, with first-person references rewritten."""
    ordered = sorted(i for i in indices if parse.tokens[i].pos != "PUNCT" or i != max(indices))
    first_person_subject_heads = {
        parse.tokens[i].head
        for i in ordered
        if parse.tokens[i].lower in ("i",) and parse.tokens[i].dep in _SUBJECT_DEPS
    }
    parts: list[str] = []
    for position, i in enumerate(ordered):
        token = parse.tokens[i]
        lower = token.lower.replace(_TYPOGRAPHIC_APOSTROPHE, "'")
        text = token.text
        if lower in _FIRST_PERSON and token.pos == "PRON":
            text = _FIRST_PERSON[lower]
        elif _agrees_with_i(parse, i, first_person_subject_heads):
            text = _third_person(token)
        if (
            text != token.text
            and token.text.startswith("'")
            and parts
            and not parts[-1][-1:].isspace()
        ):
            parts[-1] += " "  # "I'm" -> "the user is", not "the useris"
        spacing = token.whitespace if position < len(ordered) - 1 else ""
        if position < len(ordered) - 1 and ordered[position + 1] != i + 1 and not spacing:
            spacing = " "
        parts.append(text + spacing)
    return "".join(parts).strip(" ,;")


def _agrees_with_i(parse: _Parse, index: int, heads: set[int]) -> bool:
    """A present-tense verb or auxiliary whose subject is "I"."""
    token = parse.tokens[index]
    if token.tag == "VB" and index in heads:  # "I no longer eat": no auxiliary carries tense
        return not _has_aux(parse, index)
    if token.tag != "VBP":
        return False
    return index in heads or (token.dep in ("aux", "auxpass") and token.head in heads)


def _third_person(token: Token) -> str:
    lower = token.lower.replace(_TYPOGRAPHIC_APOSTROPHE, "'")
    if lower in _THIRD_PERSON_VERB:
        return _THIRD_PERSON_VERB[lower]
    text = token.text
    if re.search(r"(s|sh|ch|x|z|o)$", lower):
        return text + "es"
    if re.search(r"[^aeiou]y$", lower):
        return text[:-1] + "ies"
    return text + "s"


def _spans(tokens: Sequence[Token], indices: set[int], labels: frozenset[str]) -> tuple[str, ...]:
    spans: list[list[int]] = []
    for i in sorted(indices):
        token = tokens[i]
        if token.entity not in labels:
            continue
        if spans and spans[-1][-1] == i - 1 and not token.entity_start:
            spans[-1].append(i)
        else:
            spans.append([i])
    return tuple(
        "".join(tokens[i].text + (tokens[i].whitespace if i != span[-1] else "") for i in span)
        for span in spans
    )


class FactExtractor:
    def __init__(self, settings: FactExtractionSettings) -> None:
        self._settings = settings

    def extract(
        self, content: SourceContent, selected: Sequence[SelectedSentence]
    ) -> FactExtraction:
        proposals: list[FactProposal] = []
        failed: list[tuple[int, int]] = []
        questions = 0
        for item in selected:
            if item.sentence.text.rstrip().endswith("?"):
                questions += 1  # AC-07: a question is never an assertion
                continue
            try:
                proposals.extend(self._sentence(content, item.segment, item.sentence))
            except Exception:
                failed.append((item.segment.position, item.sentence.index))
        return FactExtraction(proposals=proposals, failed=failed, skipped_questions=questions)

    def _sentence(
        self, content: SourceContent, segment: Segment, sentence: Sentence
    ) -> list[FactProposal]:
        parse = _Parse(sentence)
        clauses = _clauses(parse)
        return [self._proposal(content, segment, sentence, parse, c) for c in clauses]

    def _proposal(
        self,
        content: SourceContent,
        segment: Segment,
        sentence: Sentence,
        parse: _Parse,
        clause: _Clause,
    ) -> FactProposal:
        tokens = parse.tokens
        head = clause.head
        verb = parse.is_verb(head)
        chain = _xcomp_chain(parse, head)
        # The object of the innermost verb ("want to become [a developer]").
        objects = (parse.child(v, _OBJECT_DEPS) for v in reversed(chain))
        obj = next((o for o in objects if o is not None), None)
        stop = frozenset(i for i in range(len(tokens)) if i not in clause.tokens)
        details = [
            c
            for v in chain
            for c in parse.children[v]
            if tokens[c].dep in _DETAIL_DEPS and c != obj and tokens[c].dep != "neg"
        ]
        conditions = [
            c
            for c in parse.children[head]
            if tokens[c].dep == "advcl" and _mark(parse, c) in _CONDITION_MARKS
        ]
        subject_text = _render(parse, clause.subject) if clause.subject else None
        own_subject = parse.child(head, _SUBJECT_DEPS) is not None
        proposition_tokens = set(clause.tokens)
        if clause.subject and not own_subject:
            proposition_tokens |= set(clause.subject)
        body = _render(parse, proposition_tokens)
        if tokens[head].tag == "VBG" and not _has_aux(parse, head) and not own_subject:
            body = _insert_copula(body, subject_text)
        if clause.attributed_to:
            body = f"according to {_render(parse, clause.attributed_to)}, {body}"
        proposition = body[:1].upper() + body[1:]
        if not proposition.endswith((".", "!")):
            proposition += "."
        unresolved = tuple(
            tokens[i].text
            for i in sorted(clause.tokens | set(clause.subject))
            if tokens[i].lower in _UNRESOLVED and tokens[i].pos == "PRON"
        )
        modality = _modality(parse, head, chain, bool(conditions), clause.believed)
        weaknesses = []
        if not clause.subject:
            weaknesses.append(NO_SUBJECT)
        if not verb:
            weaknesses.append(NO_VERB)
        if unresolved:
            weaknesses.append(UNRESOLVED_REFERENCE)
        if verb and obj is None and not details and len(chain) == 1:
            weaknesses.append(NO_OBJECT)
        if len(tokens) > self._settings.long_sentence_tokens:
            weaknesses.append(LONG_SENTENCE)
        confidence = self._confidence(weaknesses)
        status, reason = self._status(confidence, bool(unresolved))
        clause_text = {i for i in clause.tokens}
        return FactProposal(
            id=new_id(),
            owner_id=content.source.owner_id,
            source_id=content.source.id,
            segment=segment.position,
            sentence=sentence.index,
            original_text=sentence.text,
            proposition=proposition,
            subject=subject_text,
            predicate=" to ".join(tokens[v].lemma for v in chain) if verb else None,
            object=_render(parse, parse.subtree(obj, stop)) if obj is not None else None,
            attributes=tuple(_render(parse, parse.subtree(c, stop)) for c in sorted(details)),
            modality=modality,
            negated=_negated(parse, chain),
            conditions=tuple(_render(parse, parse.subtree(c)) for c in conditions),
            temporal=_spans(tokens, clause_text, _TEMPORAL_ENTITIES),
            temporal_reference=segment.sent_at or content.source.received_at.isoformat(),
            quantities=tuple(
                q
                for q in _spans(tokens, clause_text, _QUANTITY_ENTITIES)
                if q not in _spans(tokens, clause_text, _TEMPORAL_ENTITIES)
            ),
            speaker=segment.speaker or "user",
            attributed_to=_render(parse, clause.attributed_to) if clause.attributed_to else None,
            correction=bool(_CORRECTION.search(sentence.text.lower())),
            unresolved_references=unresolved,
            weaknesses=tuple(weaknesses),
            extraction_confidence=confidence,
            status=status,
            reason_code=reason,
            method=METHOD,
            method_version=METHOD_VERSION,
        )

    def _confidence(self, weaknesses: Sequence[str]) -> float:
        s = self._settings
        penalties = {
            NO_SUBJECT: s.penalty_no_subject,
            NO_VERB: s.penalty_no_verb,
            UNRESOLVED_REFERENCE: s.penalty_unresolved_reference,
            NO_OBJECT: s.penalty_no_object,
            LONG_SENTENCE: s.penalty_long_sentence,
        }
        return round(max(0.0, 1.0 - sum(penalties[w] for w in weaknesses)), 4)

    def _status(self, confidence: float, unresolved: bool) -> tuple[ProposalStatus, str | None]:
        if confidence < self._settings.reject_threshold:
            return ProposalStatus.REJECTED, LOW_EXTRACTION_CONFIDENCE
        if unresolved:
            return ProposalStatus.NEEDS_REVIEW, UNRESOLVED_REFERENCE
        if confidence < self._settings.review_threshold:
            return ProposalStatus.NEEDS_REVIEW, LOW_EXTRACTION_CONFIDENCE
        return ProposalStatus.EXTRACTED, None


def _mark(parse: _Parse, index: int) -> str | None:
    mark = parse.child(index, ("mark",))
    return None if mark is None else parse.tokens[mark].lower


def _has_aux(parse: _Parse, index: int) -> bool:
    return parse.child(index, ("aux", "auxpass")) is not None


def _insert_copula(body: str, subject: str | None) -> str:
    """'the user currently learning Kotlin' -> 'the user is currently learning Kotlin'."""
    if subject and body.startswith(subject + " "):
        return f"{subject} is {body[len(subject) + 1 :]}"
    return body


def _xcomp_chain(parse: _Parse, head: int) -> list[int]:
    chain = [head]
    while (nxt := parse.child(chain[-1], ("xcomp",))) is not None and parse.is_verb(nxt):
        chain.append(nxt)
    return chain


def _negated(parse: _Parse, chain: Sequence[int]) -> bool:
    for verb in chain:
        for child in parse.children[verb]:
            token = parse.tokens[child]
            if token.dep == "neg" or token.lower == "never":
                return True
            if token.lower == "longer" and any(
                parse.tokens[g].lower == "no" for g in parse.children[child]
            ):
                return True
    return False


def _modality(
    parse: _Parse, head: int, chain: Sequence[int], conditional: bool, believed: bool
) -> FactModality:
    if conditional:
        return FactModality.CONDITIONAL
    tokens = parse.tokens
    words = {tokens[c].lower for v in chain for c in parse.children[v]}
    if believed or words & (_POSSIBLE_AUX | _HEDGES):
        return FactModality.POSSIBLE
    if "would" in words:
        return FactModality.INTENDED if tokens[head].lemma == "like" else FactModality.POSSIBLE
    going_to = tokens[head].lemma == "go" and len(chain) > 1 and tokens[head].tag == "VBG"
    if words & _FUTURE_AUX or going_to or tokens[head].lemma in _INTENT:
        return FactModality.INTENDED
    return FactModality.FACTUAL


def _clauses(parse: _Parse) -> list[_Clause]:
    tokens = parse.tokens
    root = next((i for i, t in enumerate(tokens) if t.dep == "ROOT"), 0)
    heads: list[tuple[int, tuple[int, ...], tuple[int, ...], bool]] = []
    pending: list[tuple[int, tuple[int, ...], tuple[int, ...], bool]] = [(root, (), (), False)]
    while pending:
        head, inherited, reporter, believed = pending.pop(0)
        subject_index = parse.child(head, _SUBJECT_DEPS)
        subject = (
            tuple(sorted(parse.subtree(subject_index))) if subject_index is not None else inherited
        )
        lemma = tokens[head].lemma
        for child in parse.children[head]:
            dep = tokens[child].dep
            if (dep == "conj" and parse.is_verb(child)) or (
                dep == "advcl" and _participial(parse, head, child)
            ):
                pending.append((child, subject, reporter, believed))
            elif dep == "ccomp" and lemma in _REPORTING:
                pending.append((child, (), subject, believed))
            elif dep == "ccomp" and lemma in _BELIEF and _is_user(tokens, subject):
                pending.append((child, (), reporter, True))
        heads.append((head, subject, reporter, believed))
    separate = {h for h, *_ in heads}
    clauses = []
    for head, subject, reporter, believed in heads:
        lemma = tokens[head].lemma
        stop = frozenset(separate - {head})
        members = parse.subtree(head, stop)
        members -= {c for c in parse.children[head] if tokens[c].dep == "cc"}
        if reporter or believed:  # "... said [that] the project is cancelled"
            members -= {c for c in parse.children[head] if tokens[c].dep == "mark"}
        is_frame = any(
            tokens[c].dep == "ccomp" and c in separate for c in parse.children[head]
        ) and (lemma in _REPORTING or lemma in _BELIEF)
        if is_frame:
            continue  # "my friend said ..." / "I think ...": the frame is not a fact
        members -= set(subject) if parse.child(head, _SUBJECT_DEPS) is None else set()
        clauses.append(
            _Clause(
                head=head,
                tokens=frozenset(members),
                subject=subject,
                attributed_to=reporter,
                believed=believed,
            )
        )
    return clauses


def _participial(parse: _Parse, head: int, clause: int) -> bool:
    """ ", currently learning Kotlin": a comma-separated participle without its own
    subject or marker is a separate fact; "go running" is not."""
    token = parse.tokens[clause]
    if token.tag != "VBG" or _mark(parse, clause) is not None:
        return False
    if parse.child(clause, _SUBJECT_DEPS) is not None:
        return False
    start = min(parse.subtree(clause))
    return any(parse.tokens[i].text == "," for i in range(min(head, start) + 1, start))


def _is_user(tokens: Sequence[Token], subject: tuple[int, ...]) -> bool:
    return any(tokens[i].lower in ("i", "we") for i in subject)


class FactExtractionStage:
    """The pipeline stage after the gate: extract proposals, then evaluate (steps 4-5)."""

    def __init__(self, extractor: FactExtractor, downstream: ProposalStage) -> None:
        self._extractor = extractor
        self._downstream = downstream

    def extract(
        self, content: SourceContent, selected: Sequence[SelectedSentence]
    ) -> PipelineResult:
        return self._downstream.evaluate(content, self._extractor.extract(content, selected))
