"""The English-first language check (G6; owner-approved, 8.4 step 1).

Deterministic and dependency-free, so the outcome is reproducible and
auditable (6.2 section 2.4):

1. If more than ``max_non_latin_letter_share`` of the letters are outside the
   Latin script, the text is not English.
2. Texts with fewer than ``min_words`` words are otherwise treated as English:
   too short to judge, and premature rejection could lose meaning (6.2.2
   section 4.7).
3. Longer texts are English when at least ``min_function_word_share`` of
   their words are common English function words (articles, pronouns,
   auxiliaries, prepositions, conjunctions). Content words vary by topic;
   function words do not.

A "not English" answer defers the source with ``UNSUPPORTED_LANGUAGE``; it
never discards it. Thresholds are uncalibrated defaults (Decision 14) and are
checked against ``tests/memory_engine/quality/data/language``.
"""

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass

from memory_engine.config.settings import ExtractionSettings

UNSUPPORTED_LANGUAGE = "UNSUPPORTED_LANGUAGE"
_TYPOGRAPHIC_APOSTROPHE = chr(0x2019)  # right single quotation mark

_WORD = re.compile(r"[^\W\d_]+(?:'[^\W\d_]+)?")

ENGLISH_FUNCTION_WORDS = frozenset(
    [
        "a",
        "about",
        "above",
        "after",
        "again",
        "against",
        "all",
        "am",
        "an",
        "and",
        "any",
        "are",
        "as",
        "at",
        "be",
        "because",
        "been",
        "before",
        "being",
        "below",
        "between",
        "both",
        "but",
        "by",
        "can",
        "could",
        "did",
        "do",
        "does",
        "doing",
        "down",
        "during",
        "each",
        "few",
        "for",
        "from",
        "further",
        "had",
        "has",
        "have",
        "having",
        "he",
        "her",
        "here",
        "hers",
        "herself",
        "him",
        "himself",
        "his",
        "how",
        "i",
        "if",
        "in",
        "into",
        "is",
        "it",
        "its",
        "itself",
        "just",
        "me",
        "might",
        "more",
        "most",
        "must",
        "my",
        "myself",
        "no",
        "nor",
        "not",
        "now",
        "of",
        "off",
        "on",
        "once",
        "only",
        "or",
        "other",
        "our",
        "ours",
        "ourselves",
        "out",
        "over",
        "own",
        "same",
        "shall",
        "she",
        "should",
        "so",
        "some",
        "such",
        "than",
        "that",
        "the",
        "their",
        "theirs",
        "them",
        "themselves",
        "then",
        "there",
        "these",
        "they",
        "this",
        "those",
        "through",
        "to",
        "too",
        "under",
        "until",
        "up",
        "us",
        "very",
        "was",
        "we",
        "were",
        "what",
        "when",
        "where",
        "which",
        "while",
        "who",
        "whom",
        "why",
        "will",
        "with",
        "would",
        "you",
        "your",
        "yours",
        "yourself",
        "yourselves",
        "i'm",
        "i've",
        "i'll",
        "i'd",
        "it's",
        "don't",
        "doesn't",
        "didn't",
        "can't",
        "won't",
        "isn't",
        "aren't",
        "wasn't",
        "weren't",
        "that's",
        "there's",
        "let's",
        "we're",
        "they're",
        "you're",
    ]
)


@dataclass(frozen=True, slots=True, kw_only=True)
class LanguagePolicy:
    min_words: int
    min_function_word_share: float
    max_non_latin_letter_share: float


def language_policy(settings: ExtractionSettings) -> LanguagePolicy:
    return LanguagePolicy(
        min_words=settings.language_min_words,
        min_function_word_share=settings.english_min_function_word_share,
        max_non_latin_letter_share=settings.max_non_latin_letter_share,
    )


@dataclass(frozen=True, slots=True)
class LanguageAssessment:
    english: bool
    words: int
    function_word_share: float | None
    non_latin_letter_share: float
    reason_code: str | None  # UNSUPPORTED_LANGUAGE when not English


def _is_latin(letter: str) -> bool:
    return unicodedata.name(letter, "").startswith("LATIN ")  # unnamed: not Latin


def assess(texts: Iterable[str], policy: LanguagePolicy) -> LanguageAssessment:
    """Decide whether the combined texts are English under ``policy``."""
    text = "\n".join(texts)
    letters = [c for c in text if c.isalpha()]
    non_latin = sum(1 for c in letters if not _is_latin(c))
    non_latin_share = non_latin / len(letters) if letters else 0.0
    words = [w.lower() for w in _WORD.findall(text.replace(_TYPOGRAPHIC_APOSTROPHE, "'"))]
    if non_latin_share > policy.max_non_latin_letter_share:
        return LanguageAssessment(False, len(words), None, non_latin_share, UNSUPPORTED_LANGUAGE)
    if len(words) < policy.min_words:
        return LanguageAssessment(True, len(words), None, non_latin_share, None)
    share = sum(1 for w in words if w in ENGLISH_FUNCTION_WORDS) / len(words)
    english = share >= policy.min_function_word_share
    return LanguageAssessment(
        english, len(words), share, non_latin_share, None if english else UNSUPPORTED_LANGUAGE
    )
