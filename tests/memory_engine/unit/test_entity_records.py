"""Domain invariants of entities, mentions, resolution records and relationships."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from memory_engine.domain.errors import DomainValidationError
from memory_engine.domain.identifiers import new_id
from memory_engine.domain.vocabulary import (
    EntityRelationshipType,
    EntityResolutionOutcome,
    EntityScope,
    EntityStatus,
    EntityType,
    MemoryRelationshipType,
    MentionResolutionStatus,
    ProvenanceOriginKind,
    SupersessionReason,
)
from memory_engine.personal.domain import (
    Entity,
    EntityAlias,
    EntityMention,
    EntityRelationship,
    EntityResolutionRecord,
    MemoryRelationship,
    ordered_pair,
)

T0 = datetime(2026, 11, 1, 9, 0, tzinfo=UTC)
OWNER = uuid.UUID("00000000-0000-4000-8000-000000000003")


def entity(**overrides: Any) -> Entity:
    values: dict[str, Any] = {
        "id": new_id(),
        "owner_id": OWNER,
        "entity_type": EntityType.PERSON,
        "canonical_name": "Synthetic Person",
        "status": EntityStatus.ACTIVE,
    }
    return Entity(**{**values, **overrides})


def record(outcome: EntityResolutionOutcome, **overrides: Any) -> EntityResolutionRecord:
    values: dict[str, Any] = {
        "id": new_id(),
        "owner_id": OWNER,
        "outcome": outcome,
        "recorded_at": T0,
    }
    return EntityResolutionRecord(**{**values, **overrides})


# --- entities and aliases ----------------------------------------------------------


def test_shared_entities_are_not_permitted_yet() -> None:
    with pytest.raises(DomainValidationError, match="Decision 11"):
        entity(scope=EntityScope.SHARED)


def test_merged_entities_name_a_different_survivor() -> None:
    survivor = new_id()
    entity(status=EntityStatus.MERGED, merged_into_id=survivor)
    with pytest.raises(DomainValidationError, match="exactly when merged"):
        entity(status=EntityStatus.MERGED)
    with pytest.raises(DomainValidationError, match="exactly when merged"):
        entity(merged_into_id=survivor)
    same = new_id()
    with pytest.raises(DomainValidationError, match="itself"):
        entity(id=same, status=EntityStatus.MERGED, merged_into_id=same)


def test_unknown_type_keeps_uncertainty() -> None:
    assert entity(entity_type=EntityType.UNKNOWN).entity_type is EntityType.UNKNOWN
    with pytest.raises(DomainValidationError):
        entity(canonical_name="  ")


@pytest.mark.parametrize(
    ("text", "key"),
    [("  Company   X ", "company x"), ("COMPANY X", "company x"), ("Straße", "strasse")],
)
def test_alias_normalization(text: str, key: str) -> None:
    assert EntityAlias.normalize(text) == key


# --- mentions -----------------------------------------------------------------------


def test_resolved_mentions_and_only_they_name_an_entity() -> None:
    base: dict[str, Any] = {
        "id": new_id(),
        "owner_id": OWNER,
        "source_id": new_id(),
        "mention_text": "Dr. Synthetic",
        "mention_type": EntityType.PERSON,
    }
    EntityMention(**base, resolution_status=MentionResolutionStatus.RESOLVED, entity_id=new_id())
    EntityMention(**base, resolution_status=MentionResolutionStatus.AMBIGUOUS)
    with pytest.raises(DomainValidationError):
        EntityMention(**base, resolution_status=MentionResolutionStatus.RESOLVED)
    with pytest.raises(DomainValidationError):
        EntityMention(
            **base, resolution_status=MentionResolutionStatus.UNRESOLVED, entity_id=new_id()
        )
    with pytest.raises(DomainValidationError):
        EntityMention(**base, resolution_status=MentionResolutionStatus.UNRESOLVED, confidence=1.2)


# --- resolution records --------------------------------------------------------------


@pytest.mark.parametrize(
    ("outcome", "kwargs", "status"),
    [
        (
            EntityResolutionOutcome.MATCHED_EXISTING,
            {"mention_id": "m", "entity_id": "e"},
            MentionResolutionStatus.RESOLVED,
        ),
        (
            EntityResolutionOutcome.CREATED_NEW,
            {"mention_id": "m", "entity_id": "e"},
            MentionResolutionStatus.RESOLVED,
        ),
        (
            EntityResolutionOutcome.LEFT_UNRESOLVED,
            {"mention_id": "m"},
            MentionResolutionStatus.UNRESOLVED,
        ),
        (
            EntityResolutionOutcome.LEFT_UNRESOLVED,
            {"mention_id": "m", "candidate_entity_ids": ("a", "b")},
            MentionResolutionStatus.AMBIGUOUS,
        ),
        (
            EntityResolutionOutcome.SENT_TO_REVIEW,
            {"mention_id": "m"},
            MentionResolutionStatus.NEEDS_REVIEW,
        ),
        (
            EntityResolutionOutcome.CORRECTED,
            {"mention_id": "m", "entity_id": "e", "previous_entity_id": "p"},
            MentionResolutionStatus.RESOLVED,
        ),
    ],
)
def test_outcomes_imply_mention_states(
    outcome: EntityResolutionOutcome, kwargs: dict[str, Any], status: MentionResolutionStatus
) -> None:
    ids = {"m": new_id(), "e": new_id(), "p": new_id(), "a": new_id(), "b": new_id()}
    resolved = {
        key: tuple(ids[v] for v in value) if isinstance(value, tuple) else ids[value]
        for key, value in kwargs.items()
    }
    assert record(outcome, **resolved).mention_status() is status


@pytest.mark.parametrize(
    ("outcome", "kwargs"),
    [
        (EntityResolutionOutcome.MATCHED_EXISTING, {"mention_id": True}),  # no entity
        (EntityResolutionOutcome.LEFT_UNRESOLVED, {"mention_id": True, "entity_id": True}),
        (EntityResolutionOutcome.MERGED, {"entity_id": True}),  # no previous entity
        (
            EntityResolutionOutcome.MERGED,
            {"entity_id": True, "previous_entity_id": True, "mention_id": True},
        ),
        (EntityResolutionOutcome.REASSIGNED, {"mention_id": True, "entity_id": True}),
        (EntityResolutionOutcome.CREATED_NEW, {"entity_id": True}),  # no mention
    ],
)
def test_outcomes_reject_inconsistent_references(
    outcome: EntityResolutionOutcome, kwargs: dict[str, bool]
) -> None:
    with pytest.raises(DomainValidationError):
        record(outcome, **{key: new_id() for key in kwargs})


def test_merge_record_needs_two_different_entities_and_resolves_no_mention() -> None:
    same = new_id()
    with pytest.raises(DomainValidationError, match="differ"):
        record(EntityResolutionOutcome.MERGED, entity_id=same, previous_entity_id=same)
    merge = record(EntityResolutionOutcome.MERGED, entity_id=new_id(), previous_entity_id=new_id())
    with pytest.raises(DomainValidationError, match="does not resolve"):
        merge.mention_status()


# --- relationships -------------------------------------------------------------------


def test_symmetric_relationships_are_stored_once_in_canonical_order() -> None:
    a, b = new_id(), new_id()
    low, high = ordered_pair(a, b)
    assert low < high and {low, high} == {a, b}
    EntityRelationship(
        id=new_id(),
        owner_id=OWNER,
        source_entity_id=low,
        target_entity_id=high,
        relationship_type=EntityRelationshipType.KNOWS,
        origin_kind=ProvenanceOriginKind.EXPLICIT,
        recorded_at=T0,
    )
    with pytest.raises(DomainValidationError, match="ordered_pair"):
        EntityRelationship(
            id=new_id(),
            owner_id=OWNER,
            source_entity_id=high,
            target_entity_id=low,
            relationship_type=EntityRelationshipType.KNOWS,
            origin_kind=ProvenanceOriginKind.EXPLICIT,
            recorded_at=T0,
        )
    # Directed types keep the caller's direction.
    EntityRelationship(
        id=new_id(),
        owner_id=OWNER,
        source_entity_id=high,
        target_entity_id=low,
        relationship_type=EntityRelationshipType.WORKS_AT,
        origin_kind=ProvenanceOriginKind.EXPLICIT,
        recorded_at=T0,
    )


def test_relationships_need_distinct_endpoints_and_ordered_time() -> None:
    same = new_id()
    with pytest.raises(DomainValidationError, match="different endpoints"):
        EntityRelationship(
            id=new_id(),
            owner_id=OWNER,
            source_entity_id=same,
            target_entity_id=same,
            relationship_type=EntityRelationshipType.WORKS_AT,
            origin_kind=ProvenanceOriginKind.EXPLICIT,
            recorded_at=T0,
        )
    with pytest.raises(DomainValidationError, match="valid_to"):
        EntityRelationship(
            id=new_id(),
            owner_id=OWNER,
            source_entity_id=new_id(),
            target_entity_id=new_id(),
            relationship_type=EntityRelationshipType.WORKS_AT,
            origin_kind=ProvenanceOriginKind.EXPLICIT,
            recorded_at=T0,
            valid_from=T0,
            valid_to=T0 - timedelta(days=1),
        )


def test_supersedes_and_only_supersedes_carries_a_reason() -> None:
    base: dict[str, Any] = {
        "id": new_id(),
        "owner_id": OWNER,
        "source_memory_id": new_id(),
        "target_memory_id": new_id(),
        "origin_kind": ProvenanceOriginKind.SYSTEM_GENERATED,
        "recorded_at": T0,
    }
    MemoryRelationship(
        **base,
        relationship_type=MemoryRelationshipType.SUPERSEDES,
        reason=SupersessionReason.TEMPORAL_CHANGE,
    )
    with pytest.raises(DomainValidationError, match="reason"):
        MemoryRelationship(**base, relationship_type=MemoryRelationshipType.SUPERSEDES)
    with pytest.raises(DomainValidationError, match="reason"):
        MemoryRelationship(
            **base,
            relationship_type=MemoryRelationshipType.SUPPORTS,
            reason=SupersessionReason.REPLACEMENT,
        )


def test_symmetric_vocabulary_matches_the_amendment() -> None:
    assert {t for t in EntityRelationshipType if t.symmetric} == {
        EntityRelationshipType.KNOWS,
        EntityRelationshipType.RELATED_TO,
    }
    assert {t for t in MemoryRelationshipType if t.symmetric} == {
        MemoryRelationshipType.CONTRADICTS,
        MemoryRelationshipType.RELATED_TO,
    }
