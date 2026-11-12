"""The relevance gate (6.2.2; owner-approved design, 8.4 step 2).

Each sentence of each user-authored segment is judged; assistant and other
speakers' turns give context only. Per sentence, in order:

1. **Explicit protection** (6.2.2 section 4.7) forces ``process``: an explicit
   remember instruction on the source, a "remember that" phrase, a correction.
2. **Deterministic rejection:** small talk, questions and hypotheticals
   (6.2.3 section 5.5: a question or hypothetical is not a fact). Then a
   significant life event the user takes part in is protected (``process``).
3. **Score** (6.2.2 section 4.5): a weighted mean of the signals that could be
   evaluated (missing ones are left out, never zero): personal relevance,
   long-term utility, temporal significance, contextual significance (only in
   conversations), information density. ``process`` at or above the process
   threshold; ``defer`` (``AMBIGUOUS_RELEVANCE``) between the thresholds;
   ``reject`` below, with the most specific reason.

Roll-up to the source: any processed sentence -> ``process`` (extraction
continues with those sentences); otherwise any deferral -> ``defer``;
otherwise ``reject``. The reason is the most frequent unit reason. If the
analyzer fails, the source is deferred with ``ANALYSIS_UNAVAILABLE`` (6.2.2
section 4.10: "NLP failure: use safe fallback or defer").

Weights and thresholds are uncalibrated defaults (6.2.2 section 4.5),
checked against ``tests/memory_engine/quality/data/relevance``.
"""

import re
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Protocol

from memory_engine.config.settings import RelevanceSettings
from memory_engine.domain.identifiers import new_id
from memory_engine.domain.vocabulary import (
    InstructionType,
    RelevanceOutcome,
    SourceProcessingStatus,
)
from memory_engine.personal.application.analysis import Sentence, SentenceAnalyzer, Token
from memory_engine.personal.application.extraction import (
    PipelineResult,
    Segment,
    SourceContent,
)
from memory_engine.personal.domain import RelevanceAssessment, UnitAssessment

METHOD = "relevance_gate"
_TYPOGRAPHIC_APOSTROPHE = chr(0x2019)
METHOD_VERSION = "1"

# Reason codes (reject and defer) and protection codes (forced processing).
SMALL_TALK = "SMALL_TALK"
QUESTION_ONLY = "QUESTION_ONLY"
HYPOTHETICAL = "HYPOTHETICAL"
GENERAL_KNOWLEDGE = "GENERAL_KNOWLEDGE"
THIRD_PARTY_ONLY = "THIRD_PARTY_ONLY"
LOW_INFORMATION = "LOW_INFORMATION"
NOT_PERSONALLY_RELEVANT = "NOT_PERSONALLY_RELEVANT"
AMBIGUOUS_RELEVANCE = "AMBIGUOUS_RELEVANCE"
ANALYSIS_UNAVAILABLE = "ANALYSIS_UNAVAILABLE"
NO_USER_CONTENT = "NO_USER_CONTENT"
EXPLICIT_REMEMBER = "EXPLICIT_REMEMBER"
REMEMBER_PHRASE = "REMEMBER_PHRASE"
CORRECTION = "CORRECTION"
SIGNIFICANT_EVENT = "SIGNIFICANT_EVENT"

_FIRST_PERSON_SUBJECT = frozenset({"i", "we"})
_FIRST_PERSON_OTHER = frozenset({"me", "us", "my", "our", "mine", "ours", "myself", "ourselves"})
_THIRD_PERSON = frozenset({"he", "she", "they", "him", "her", "them", "his", "their"})
_SMALL_TALK_WORDS = frozenset(
    [
        "hi",
        "hello",
        "hey",
        "thanks",
        "thank",
        "you",
        "thx",
        "ok",
        "okay",
        "cool",
        "great",
        "nice",
        "lol",
        "haha",
        "bye",
        "goodbye",
        "good",
        "morning",
        "night",
        "evening",
        "afternoon",
        "sure",
        "yes",
        "no",
        "yep",
        "nope",
        "yeah",
        "fine",
        "got",
        "it",
        "sounds",
        "same",
        "too",
        "welcome",
        "cheers",
        "alright",
        "awesome",
        "perfect",
    ]
)
_HYPOTHETICAL_OPENERS = (
    "imagine",
    "suppose",
    "supposing",
    "what if",
    "hypothetically",
    "pretend",
    "let's say",
    "lets say",
    "in theory",
    "assume",
)
_REMEMBER_PHRASES = re.compile(
    r"\b(remember that|please remember|remember:|don't forget|do not forget|keep in mind|"
    r"note that|for the record)\b"
)
_CORRECTION = re.compile(
    r"^(actually|correction|to clarify|i meant|i mean|sorry, i meant)\b|"
    r"\b(not anymore|no longer|i was wrong|scratch that)\b"
)
_LIFE_EVENT_LEMMAS = frozenset(
    [
        "marry",
        "divorce",
        "die",
        "graduate",
        "diagnose",
        "hire",
        "retire",
        "move",
        "engage",
        "adopt",
        "promote",
        "relocate",
        "resign",
        "quit",
        "bear",
    ]
)
_LIFE_EVENT_WORDS = frozenset(
    [
        "born",
        "pregnant",
        "wedding",
        "funeral",
        "surgery",
        "engaged",
        "married",
        "divorced",
        "graduated",
    ]
)
_UTILITY_LEMMAS = frozenset(
    [
        "prefer",
        "like",
        "love",
        "hate",
        "dislike",
        "enjoy",
        "want",
        "plan",
        "decide",
        "choose",
        "intend",
        "aim",
        "hope",
        "need",
        "promise",
        "commit",
        "work",
        "live",
        "study",
        "learn",
        "own",
        "use",
        "allergic",
        "favourite",
        "favorite",
        "goal",
        "start",
        "stop",
        "switch",
        "join",
        "leave",
        "buy",
        "sell",
        "build",
        "train",
        "practice",
        "avoid",
        "follow",
        "drive",
        "cook",
        "play",
        "speak",
        "teach",
        "manage",
        "lead",
        "run",
        "will",
    ]
)
_TEMPORAL_LEMMAS = frozenset(
    [
        "tomorrow",
        "tonight",
        "today",
        "yesterday",
        "deadline",
        "birthday",
        "anniversary",
        "appointment",
        "meeting",
        "exam",
        "interview",
        "weekend",
    ]
)
_TEMPORAL_ENTITIES = frozenset({"DATE", "TIME"})
_CONTENT_POS = frozenset({"NOUN", "PROPN", "VERB", "ADJ", "NUM"})


@dataclass(frozen=True, slots=True, kw_only=True)
class RelevancePolicy:
    weights: dict[str, float]
    process_threshold: float
    defer_threshold: float

    @classmethod
    def from_settings(cls, settings: RelevanceSettings) -> "RelevancePolicy":
        return cls(
            weights={
                "personal": settings.weight_personal,
                "utility": settings.weight_utility,
                "temporal": settings.weight_temporal,
                "context": settings.weight_context,
                "density": settings.weight_density,
            },
            process_threshold=settings.process_threshold,
            defer_threshold=settings.defer_threshold,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class SelectedSentence:
    """A sentence the gate sends to fact extraction (6.2.3)."""

    segment: Segment
    sentence: Sentence
    unit: UnitAssessment


@dataclass(frozen=True, slots=True, kw_only=True)
class GateDecision:
    assessment: RelevanceAssessment
    selected: Sequence[SelectedSentence]


class ExtractionStage(Protocol):
    """Fact extraction onwards (steps 3-5): only the gate's selected sentences."""

    def extract(
        self, content: SourceContent, selected: Sequence[SelectedSentence]
    ) -> PipelineResult: ...


def _normalized(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().replace(_TYPOGRAPHIC_APOSTROPHE, "'")).strip()


def _is_small_talk(tokens: Sequence[Token]) -> bool:
    words = [t.lower for t in tokens if t.pos not in ("PUNCT", "SYM", "SPACE")]
    return bool(words) and all(w in _SMALL_TALK_WORDS for w in words)


def _is_question(sentence: Sentence) -> bool:
    return sentence.text.rstrip().endswith("?")


def _is_hypothetical(text: str) -> bool:
    return text.startswith(_HYPOTHETICAL_OPENERS) or "hypothetically" in text


def _personal(tokens: Sequence[Token]) -> float:
    """1: the user is the subject; 0.7: the subject is the user's (my sister);
    0.6: the user appears otherwise; 0.1: only other people; 0: no one."""
    for token in tokens:
        if token.dep.startswith("nsubj") and token.lower in _FIRST_PERSON_SUBJECT:
            return 1.0
    for token in tokens:
        if token.lower in ("my", "our") and token.dep == "poss":
            head = tokens[token.head] if 0 <= token.head < len(tokens) else None
            if head is not None and head.dep.startswith("nsubj"):
                return 0.7
    if any(t.lower in _FIRST_PERSON_SUBJECT | _FIRST_PERSON_OTHER for t in tokens):
        return 0.6
    if any(t.lower in _THIRD_PERSON or t.entity == "PERSON" for t in tokens):
        return 0.1
    return 0.0


def _signals(
    sentence: Sentence, text: str, previous_turn: Segment | None, conversation: bool
) -> dict[str, float]:
    tokens = sentence.tokens
    content = [t for t in tokens if t.pos in _CONTENT_POS and not t.is_stop]
    signals = {
        "personal": _personal(tokens),
        "utility": 1.0 if any(t.lemma in _UTILITY_LEMMAS for t in tokens) else 0.0,
        "temporal": (
            1.0
            if any(t.entity in _TEMPORAL_ENTITIES or t.lemma in _TEMPORAL_LEMMAS for t in tokens)
            else 0.0
        ),
        "density": min(1.0, len(content) / 4),
    }
    if conversation:  # context exists only when there are other turns
        answers = (
            previous_turn is not None
            and not previous_turn.from_user
            and previous_turn.text.rstrip().endswith("?")
        )
        signals["context"] = 1.0 if (answers or _CORRECTION.search(text)) else 0.3
        if answers and signals["personal"] == 0.0:
            # An answer to Raven's question with no one else named is about the user.
            signals["personal"] = 0.6
    return signals


def _significant_event(sentence: Sentence, signals: dict[str, float]) -> bool:
    """A life event the user takes part in (6.2.2 section 4.7: significant personal events)."""
    involves_user = signals["personal"] >= 0.6
    return involves_user and any(
        t.lemma in _LIFE_EVENT_LEMMAS or t.lower in _LIFE_EVENT_WORDS for t in sentence.tokens
    )


def _score(signals: dict[str, float], policy: RelevancePolicy) -> float:
    present = {k: w for k, w in policy.weights.items() if k in signals and w > 0}
    total = sum(present.values())
    return round(sum(w * signals[k] for k, w in present.items()) / total, 4)


def _reject_reason(signals: dict[str, float]) -> str:
    if signals["personal"] == 0.0:
        return GENERAL_KNOWLEDGE
    if signals["personal"] <= 0.1:
        return THIRD_PARTY_ONLY
    if signals["density"] < 0.5:
        return LOW_INFORMATION
    return NOT_PERSONALLY_RELEVANT


def _utc_now() -> datetime:
    return datetime.now(UTC)


class RelevanceGate:
    def __init__(
        self,
        analyzer: SentenceAnalyzer,
        policy: RelevancePolicy,
        *,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._analyzer = analyzer
        self._policy = policy
        self._clock = clock

    @property
    def method_version(self) -> str:
        return f"{METHOD_VERSION}+{self._analyzer.version}"

    def assess(self, content: SourceContent) -> GateDecision:
        source = content.source
        segments = list(content.segments)
        conversation = len(segments) > 1
        units: list[UnitAssessment] = []
        selected: list[SelectedSentence] = []
        user_segments = [s for s in segments if s.from_user]
        try:
            for position, segment in enumerate(segments):
                if not segment.from_user:
                    continue
                previous = segments[position - 1] if position > 0 else None
                for sentence in self._analyzer.analyze(segment.text):
                    unit = self._unit(
                        source.instruction_type, segment, sentence, previous, conversation
                    )
                    units.append(unit)
                    if unit.outcome is RelevanceOutcome.PROCESS:
                        selected.append(
                            SelectedSentence(segment=segment, sentence=sentence, unit=unit)
                        )
        except Exception:
            return self._decision(content, RelevanceOutcome.DEFER, ANALYSIS_UNAVAILABLE, [], [])
        if not user_segments or not units:
            return self._decision(content, RelevanceOutcome.REJECT, NO_USER_CONTENT, units, [])
        if selected:
            return self._decision(content, RelevanceOutcome.PROCESS, None, units, selected)
        deferred = [u.reason_code for u in units if u.outcome is RelevanceOutcome.DEFER]
        if deferred:
            return self._decision(
                content, RelevanceOutcome.DEFER, _most_common(deferred), units, []
            )
        rejected = [u.reason_code for u in units]
        return self._decision(content, RelevanceOutcome.REJECT, _most_common(rejected), units, [])

    def _unit(
        self,
        instruction: InstructionType,
        segment: Segment,
        sentence: Sentence,
        previous: Segment | None,
        conversation: bool,
    ) -> UnitAssessment:
        text = _normalized(sentence.text)
        signals = _signals(sentence, text, previous, conversation)
        score = _score(signals, self._policy)
        base = UnitAssessment(
            segment=segment.position,
            sentence=sentence.index,
            outcome=RelevanceOutcome.PROCESS,
            score=score,
            signals=signals,
        )
        explicit = self._explicit_protection(instruction, text)
        if explicit is not None:
            return replace(base, protection=explicit)
        for applies, reason in (
            (_is_small_talk(sentence.tokens), SMALL_TALK),
            (_is_question(sentence), QUESTION_ONLY),
            (_is_hypothetical(text), HYPOTHETICAL),
        ):
            if applies:
                return replace(base, outcome=RelevanceOutcome.REJECT, reason_code=reason)
        if _significant_event(sentence, signals):
            return replace(base, protection=SIGNIFICANT_EVENT)
        if score >= self._policy.process_threshold:
            return base
        if score >= self._policy.defer_threshold:
            return replace(base, outcome=RelevanceOutcome.DEFER, reason_code=AMBIGUOUS_RELEVANCE)
        return replace(base, outcome=RelevanceOutcome.REJECT, reason_code=_reject_reason(signals))

    @staticmethod
    def _explicit_protection(instruction: InstructionType, text: str) -> str | None:
        if instruction is InstructionType.REMEMBER:
            return EXPLICIT_REMEMBER
        if _REMEMBER_PHRASES.search(text):
            return REMEMBER_PHRASE
        if _CORRECTION.search(text):
            return CORRECTION
        return None

    def _decision(
        self,
        content: SourceContent,
        outcome: RelevanceOutcome,
        reason: str | None,
        units: Sequence[UnitAssessment],
        selected: Sequence[SelectedSentence],
    ) -> GateDecision:
        source = content.source
        assessment = RelevanceAssessment(
            id=new_id(),
            owner_id=source.owner_id,
            source_id=source.id,
            outcome=outcome,
            reason_code=reason,
            method=METHOD,
            method_version=self.method_version,
            assessed_at=self._clock(),
            units=units,
        )
        return GateDecision(assessment=assessment, selected=selected)


def _most_common(reasons: Sequence[str | None]) -> str:
    counts = Counter(r for r in reasons if r is not None)
    best = max(counts.values())
    return next(r for r in reasons if r is not None and counts[r] == best)


class GatedPipeline:
    """The extraction pipeline from step 2 on: the gate, then fact extraction.

    Rejected and deferred sources stop here, with the gate's reason; the
    decision is persisted with the source's outcome in every case.
    """

    def __init__(self, gate: RelevanceGate, downstream: ExtractionStage) -> None:
        self._gate = gate
        self._downstream = downstream

    def run(self, content: SourceContent) -> PipelineResult:
        decision = self._gate.assess(content)
        assessment = decision.assessment
        if assessment.outcome is RelevanceOutcome.REJECT:
            return PipelineResult(
                status=SourceProcessingStatus.REJECTED,
                reason_code=assessment.reason_code,
                relevance=assessment,
            )
        if assessment.outcome is RelevanceOutcome.DEFER:
            return PipelineResult(
                status=SourceProcessingStatus.DEFERRED,
                reason_code=assessment.reason_code,
                relevance=assessment,
            )
        result = self._downstream.extract(content, decision.selected)
        return replace(result, relevance=assessment)
