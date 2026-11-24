"""Identified entity mentions (plan 8.5 section 4.1; owner-approved, 8.5 step 1).

An :class:`IdentifiedMention` lives only inside one run of the resolution
worker's entity stage: step 2 turns it into a persisted Entity Mention with a
resolution decision (Decisions 5.4.33-5.4.34). It records where a name occurs in
a validated candidate's proposition and which type the fact's own wording
supports; it never claims an identity.
"""

import re
import uuid
from dataclasses import dataclass
from enum import StrEnum

from memory_engine.domain.errors import DomainValidationError
from memory_engine.domain.vocabulary import EntityType

_RULE = re.compile(r"[a-z][a-z0-9_]{0,63}")
_NER_LABEL = re.compile(r"[A-Z][A-Z_]{0,31}")


class TypeBasis(StrEnum):
    """What decided a mention's type (7.1 section 26.5). NER never decides alone."""

    CONTEXT_RULE = "context_rule"  # the governing verb or preposition, for example "works at"
    NAME_KEYWORD = "name_keyword"  # a word of the name itself, for example "University"
    RELATION_NOUN = "relation_noun"  # a named relation, for example "the user's manager X"
    NONE = "none"  # no evidence in the fact: the type stays unknown


@dataclass(frozen=True, slots=True, kw_only=True)
class IdentifiedMention:
    """A named mention in one validated candidate's proposition.

    ``start`` and ``end`` are character offsets into the proposition;
    ``segment`` and ``sentence`` locate the evidence sentence in the source.
    ``rule`` names the context rule that applied (a fixed table key, never text
    from the input); ``ner_label`` is the analyzer's label and ``ner_agrees``
    says whether it matches the decided type.
    """

    owner_id: uuid.UUID
    source_id: uuid.UUID
    candidate_id: uuid.UUID
    name: str
    entity_type: EntityType
    basis: TypeBasis
    start: int
    end: int
    segment: int
    sentence: int
    method: str
    method_version: str
    rule: str | None = None
    ner_label: str | None = None
    ner_agrees: bool = False

    def __post_init__(self) -> None:
        if not self.name.strip() or self.name != self.name.strip():
            raise DomainValidationError("a mention name is non-empty and trimmed")
        if not 0 <= self.start < self.end or self.end - self.start != len(self.name):
            raise DomainValidationError("mention offsets must span exactly the name")
        if self.segment < 0 or self.sentence < 0:
            raise DomainValidationError("evidence locations are non-negative")
        if (self.basis is TypeBasis.NONE) != (self.entity_type is EntityType.UNKNOWN):
            raise DomainValidationError("a type without evidence is 'unknown', and only then")
        if self.rule is not None and not _RULE.fullmatch(self.rule):
            raise DomainValidationError("rule must be a lowercase table key")
        if (self.basis is TypeBasis.CONTEXT_RULE) != (self.rule is not None):
            raise DomainValidationError("a context-rule type names its rule, and only then")
        if self.ner_label is not None and not _NER_LABEL.fullmatch(self.ner_label):
            raise DomainValidationError("ner_label must be an uppercase label")
        if self.ner_agrees and self.ner_label is None:
            raise DomainValidationError("NER can only agree when it gave a label")
        if not self.method.strip() or not self.method_version.strip():
            raise DomainValidationError("method and method_version are required")
