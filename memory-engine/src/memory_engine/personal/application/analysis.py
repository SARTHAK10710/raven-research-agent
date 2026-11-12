"""Linguistic analysis port for extraction (7.1 section 25.3; 6.2.3 section 5.4).

Application code sees sentences and tokens only; the spaCy adapter lives in
``memory_engine.infrastructure.nlp``. Outputs are signals for deterministic
rules, never decisions (6.2 section 2.4).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True, kw_only=True)
class Token:
    text: str
    lower: str
    lemma: str
    pos: str  # Universal POS tag, for example NOUN, VERB, PRON
    dep: str  # dependency label, for example nsubj, poss, ROOT
    head: int  # index of the head token within the sentence
    entity: str = ""  # named-entity label, for example DATE, PERSON, or ""
    is_stop: bool = False
    tag: str = ""  # fine-grained tag, for example VBP, VBZ, PRP$
    whitespace: str = ""  # whitespace after the token in the original text
    entity_start: bool = False  # first token of a named entity (IOB "B")


@dataclass(frozen=True, slots=True, kw_only=True)
class Sentence:
    """One sentence of one segment; ``index`` counts sentences within the segment."""

    index: int
    text: str
    tokens: Sequence[Token]


class SentenceAnalyzer(Protocol):
    @property
    def version(self) -> str:
        """Identifies the model and library, recorded with every decision."""
        ...

    def analyze(self, text: str) -> Sequence[Sentence]: ...
