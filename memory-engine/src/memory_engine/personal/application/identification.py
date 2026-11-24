"""Entity identification and classification (plan 8.5 section 4.1-4.2; 6.3.4 stage 1).

Owner-approved in 8.5 step 1 (7.1 section 26.5):

- **What is read:** the proposition of a ``validated`` candidate. Offsets are
  relative to it; the evidence location (segment, sentence) comes from the
  candidate's extraction metadata. Other candidates yield nothing.
- **What is a name:** a run of proper nouns or named-entity tokens (person,
  organization, place, facility, product, event, work of art), with "of"
  between names ("University of Leeds") and a number right after a name
  ("iPhone 15"). Dates, times, numbers, calendar words and job titles are not
  names; first-person references ("the user") never are.
- **What decides the type:** the fact's own wording, in this order:
  1. a context rule on the governing verb and preposition ("works at X" ->
     organization, "lives in X" -> place, "building X" -> project, "uses X" ->
     technology, "bought X" -> product, "attending X" -> event, "meeting
     with X" -> person);
  2. a keyword of the name itself ("... University" -> institution, "...
     Marathon" -> event, "... Corp" -> organization, "Project ..." -> project),
     which also refines a context type (a school one "goes to" is an
     institution);
  3. a named relation ("the user's manager Priya Shah" -> person).
  Otherwise the type is ``unknown``. The NER label is recorded and marked as
  agreeing or not, but never decides a type on its own: the small English
  model tags PostgreSQL as a place and Docker as a person (probe, 2026-11-24).

Identification never claims identity: the registry (step 2) decides whether a
name matches an entity, and ambiguity stays unresolved for plan 8.6.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from memory_engine.domain.vocabulary import CandidateStatus, EntityType
from memory_engine.personal.application.analysis import Sentence, SentenceAnalyzer, Token
from memory_engine.personal.application.evaluation import names_relation
from memory_engine.personal.domain import IdentifiedMention, MemoryCandidate, TypeBasis

METHOD = "entity_rules"
METHOD_VERSION = "1"

# NER labels that name things; everything else (DATE, CARDINAL, ...) is not a name.
_NAME_LABELS = frozenset({"PERSON", "ORG", "GPE", "LOC", "FAC", "PRODUCT", "EVENT", "WORK_OF_ART"})
_NON_NAME_LABELS = frozenset(
    {"DATE", "TIME", "CARDINAL", "ORDINAL", "MONEY", "PERCENT", "QUANTITY"}
)
# The type each NER label would suggest, used only to report agreement.
_NER_TYPES = {
    "PERSON": EntityType.PERSON,
    "ORG": EntityType.ORGANIZATION,
    "GPE": EntityType.PLACE,
    "LOC": EntityType.PLACE,
    "FAC": EntityType.PLACE,
    "PRODUCT": EntityType.PRODUCT,
    "EVENT": EntityType.EVENT,
}
_CALENDAR = frozenset(
    {
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
        "january",
        "february",
        "march",
        "april",
        "may",
        "june",
        "july",
        "august",
        "september",
        "october",
        "november",
        "december",
    }
)
_TITLES = frozenset(
    {"ceo", "cto", "cfo", "coo", "cio", "vp", "md", "hr", "pm", "dr", "mr", "mrs", "ms"}
)
_NOT_NAMES = frozenset({"user", "i", "me", "my"}) | _CALENDAR | _TITLES

# (governing lemma, preposition or "" for a direct object) -> type, keyed by rule name.
_CONTEXT_RULES: dict[tuple[str, str], tuple[str, EntityType]] = {
    ("work", "at"): ("work_at", EntityType.ORGANIZATION),
    ("work", "for"): ("work_for", EntityType.ORGANIZATION),
    ("join", ""): ("join", EntityType.ORGANIZATION),
    ("shop", "at"): ("shop_at", EntityType.ORGANIZATION),
    ("employ", "by"): ("employed_by", EntityType.ORGANIZATION),
    ("live", "in"): ("live_in", EntityType.PLACE),
    ("move", "to"): ("move_to", EntityType.PLACE),
    ("relocate", "to"): ("relocate_to", EntityType.PLACE),
    ("travel", "to"): ("travel_to", EntityType.PLACE),
    ("visit", ""): ("visit", EntityType.PLACE),
    ("bear", "in"): ("born_in", EntityType.PLACE),
    ("graduate", "from"): ("graduate_from", EntityType.INSTITUTION),
    ("study", "at"): ("study_at", EntityType.INSTITUTION),
    ("build", ""): ("build", EntityType.PROJECT),
    ("develop", ""): ("develop", EntityType.PROJECT),
    ("work", "on"): ("work_on", EntityType.PROJECT),
    ("use", ""): ("use", EntityType.TECHNOLOGY),
    ("switch", "to"): ("switch_to", EntityType.TECHNOLOGY),
    ("switch", "from"): ("switch_from", EntityType.TECHNOLOGY),
    ("deploy", "on"): ("deploy_on", EntityType.TECHNOLOGY),
    ("code", "in"): ("code_in", EntityType.TECHNOLOGY),
    ("program", "in"): ("program_in", EntityType.TECHNOLOGY),
    ("buy", ""): ("buy", EntityType.PRODUCT),
    ("purchase", ""): ("purchase", EntityType.PRODUCT),
    ("attend", ""): ("attend", EntityType.EVENT),
    ("meet", ""): ("meet", EntityType.PERSON),
    ("meeting", "with"): ("meeting_with", EntityType.PERSON),
    ("work", "with"): ("work_with", EntityType.PERSON),
    ("build", "with"): ("build_with", EntityType.PERSON),
    ("develop", "with"): ("develop_with", EntityType.PERSON),
    ("call", ""): ("call", EntityType.PERSON),
    ("talk", "to"): ("talk_to", EntityType.PERSON),
    ("marry", ""): ("marry", EntityType.PERSON),
}
_NAME_KEYWORDS: dict[str, EntityType] = {
    "university": EntityType.INSTITUTION,
    "college": EntityType.INSTITUTION,
    "school": EntityType.INSTITUTION,
    "academy": EntityType.INSTITUTION,
    "institute": EntityType.INSTITUTION,
    "hospital": EntityType.INSTITUTION,
    "marathon": EntityType.EVENT,
    "conference": EntityType.EVENT,
    "festival": EntityType.EVENT,
    "summit": EntityType.EVENT,
    "expo": EntityType.EVENT,
    "championship": EntityType.EVENT,
    "corp": EntityType.ORGANIZATION,
    "inc": EntityType.ORGANIZATION,
    "ltd": EntityType.ORGANIZATION,
    "llc": EntityType.ORGANIZATION,
    "plc": EntityType.ORGANIZATION,
    "project": EntityType.PROJECT,
}
# A name keyword refines a context type into a more specific one.
_REFINES = {
    (EntityType.ORGANIZATION, EntityType.INSTITUTION),
    (EntityType.PLACE, EntityType.INSTITUTION),
    (EntityType.EVENT, EntityType.INSTITUTION),
    (EntityType.PLACE, EntityType.EVENT),
}
_CONTENT = frozenset({"NOUN", "PROPN", "ADJ", "NUM", "X"})
_RELATION_DEPS = frozenset({"compound", "appos", "nmod", "npadvmod", "poss"})


@dataclass(frozen=True, slots=True)
class _Span:
    sentence: Sentence
    first: int
    last: int  # inclusive

    @property
    def indexes(self) -> range:
        return range(self.first, self.last + 1)


def _name_like(token: Token) -> bool:
    if token.entity in _NON_NAME_LABELS or token.lower in _NOT_NAMES:
        return False
    # NER spans can include function words ("the", "at"); only content words name things.
    return token.pos == "PROPN" or (token.entity in _NAME_LABELS and token.pos in _CONTENT)


def _spans(sentence: Sentence) -> list[_Span]:
    tokens = sentence.tokens
    spans: list[_Span] = []
    i = 0
    while i < len(tokens):
        if not _name_like(tokens[i]):
            i += 1
            continue
        last = i
        j = i + 1
        while j < len(tokens):
            token = tokens[j]
            if _name_like(token):
                last = j
            elif token.lower == "of" and j + 1 < len(tokens) and _name_like(tokens[j + 1]):
                last = j + 1
                j += 1
            elif token.pos == "NUM" and token.entity not in ("DATE", "TIME"):
                last = j  # "iPhone 15", "Model 3"
                j += 1
                break
            else:
                break
            j += 1
        spans.append(_Span(sentence, i, last))
        i = max(j, last + 1)
    return spans


def _head(span: _Span) -> int:
    tokens = span.sentence.tokens
    for index in span.indexes:
        if tokens[index].head not in span.indexes or tokens[index].head == index:
            return index
    return span.last


def _context(tokens: Sequence[Token], index: int) -> tuple[str, str] | None:
    token = tokens[index]
    seen = {index}
    while token.dep == "conj" and token.head not in seen:  # "Python and Docker"
        seen.add(token.head)
        index = token.head
        token = tokens[index]
    if token.dep == "pobj":
        prep = tokens[token.head]
        governor = tokens[prep.head]
        if prep.lower == "with" and governor.dep in ("dobj", "obj", "pobj"):
            # "building Orion with Sam": the company is kept with the verb, not the object
            verb = tokens[governor.head]
            if governor.dep == "pobj":
                verb = tokens[verb.head]
            return verb.lemma.lower(), "with"
        return governor.lemma.lower(), prep.lower
    if token.dep in ("dobj", "obj"):
        return tokens[token.head].lemma.lower(), ""
    return None


def _related(span: _Span) -> bool:
    tokens = span.sentence.tokens
    head = tokens[_head(span)]
    if head.dep == "appos" and names_relation(tokens[head.head].lower):
        return True
    return any(
        t.head in span.indexes and t.dep in _RELATION_DEPS and names_relation(t.lower)
        for i, t in enumerate(tokens)
        if i not in span.indexes
    )


def _keyword_type(span: _Span) -> EntityType | None:
    words = [span.sentence.tokens[i].lower.rstrip(".") for i in span.indexes]
    for word in words:
        if word in _NAME_KEYWORDS:
            return _NAME_KEYWORDS[word]
    return None


def _ner_label(span: _Span) -> str | None:
    labels = [span.sentence.tokens[i].entity for i in span.indexes]
    return next((label for label in labels if label and label not in _NON_NAME_LABELS), None)


def _offsets(proposition: str, sentences: Sequence[Sentence]) -> list[list[int]]:
    """Character offset of every token of every sentence within the proposition."""
    result: list[list[int]] = []
    cursor = 0
    for sentence in sentences:
        found = proposition.find(sentence.text, cursor)
        position = found if found >= 0 else cursor
        starts = []
        for token in sentence.tokens:
            starts.append(position)
            position += len(token.text) + len(token.whitespace)
        result.append(starts)
        cursor = position
    return result


class EntityIdentifier:
    """Finds named mentions in validated candidates and types them from evidence."""

    def __init__(self, analyzer: SentenceAnalyzer) -> None:
        self._analyzer = analyzer

    def identify(self, candidate: MemoryCandidate) -> list[IdentifiedMention]:
        if candidate.status is not CandidateStatus.VALIDATED:
            return []  # 7.1 section 26.5: validated candidates only
        location = candidate.extraction_metadata.get("location", {})
        segment = int(location.get("segment", 0))
        sentence_index = int(location.get("sentence", 0))
        proposition = candidate.proposition
        sentences = self._analyzer.analyze(proposition)
        starts = _offsets(proposition, sentences)
        mentions: list[IdentifiedMention] = []
        for number, sentence in enumerate(sentences):
            for span in _spans(sentence):
                start = starts[number][span.first]
                last = sentence.tokens[span.last]
                end = starts[number][span.last] + len(last.text)
                raw = proposition[start:end]
                name = raw.rstrip(".,;:!?")
                if not name.strip():
                    continue
                end = start + len(name)
                if proposition[start:end] != name:
                    continue  # the analyzer's text does not line up; skip, never guess
                mentions.append(
                    self._mention(candidate, span, name, start, end, segment, sentence_index)
                )
        return mentions

    def _mention(
        self,
        candidate: MemoryCandidate,
        span: _Span,
        name: str,
        start: int,
        end: int,
        segment: int,
        sentence: int,
    ) -> IdentifiedMention:
        entity_type, basis, rule = _classify(span)
        ner = _ner_label(span)
        return IdentifiedMention(
            owner_id=candidate.owner_id,
            source_id=candidate.source_id,
            candidate_id=candidate.id,
            name=name,
            entity_type=entity_type,
            basis=basis,
            rule=rule,
            start=start,
            end=end,
            segment=segment,
            sentence=sentence,
            ner_label=ner,
            ner_agrees=ner is not None and _NER_TYPES.get(ner) is entity_type,
            method=METHOD,
            method_version=f"{METHOD_VERSION}+{self._analyzer.version}",
        )


def _classify(span: _Span) -> tuple[EntityType, TypeBasis, str | None]:
    tokens = span.sentence.tokens
    context = _context(tokens, _head(span))
    keyword = _keyword_type(span)
    if context is not None and context in _CONTEXT_RULES:
        rule, entity_type = _CONTEXT_RULES[context]
        if keyword is not None and (entity_type, keyword) in _REFINES:
            return keyword, TypeBasis.NAME_KEYWORD, None
        return entity_type, TypeBasis.CONTEXT_RULE, rule
    if keyword is not None:
        return keyword, TypeBasis.NAME_KEYWORD, None
    if _related(span):
        return EntityType.PERSON, TypeBasis.RELATION_NOUN, None
    return EntityType.UNKNOWN, TypeBasis.NONE, None
