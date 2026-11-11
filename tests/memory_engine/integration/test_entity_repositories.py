"""Plan 8.2 step 3: entities, mentions, resolution history and relationships (real PostgreSQL).

``build`` is the synthetic-record fixture from conftest.py; all content is synthetic.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy import Connection, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from memory_engine.domain.errors import DomainValidationError, OwnershipError
from memory_engine.domain.identifiers import OwnerScope, new_id
from memory_engine.domain.vocabulary import (
    EntityRelationshipType,
    EntityResolutionOutcome,
    EntityStatus,
    EntityType,
    MemoryEntityRole,
    MemoryRelationshipType,
    MentionResolutionStatus,
    ProvenanceOriginKind,
    SupersessionReason,
)
from memory_engine.exceptions import (
    ConcurrencyConflictError,
    PersistenceError,
    RecordNotFoundError,
)
from memory_engine.infrastructure.persistence import SqlAlchemyPersonalUnitOfWorkFactory
from memory_engine.personal.domain import (
    Entity,
    EntityAlias,
    EntityMention,
    EntityRelationship,
    EntityResolutionRecord,
    MemoryEntityAssociation,
    MemoryRelationship,
    ordered_pair,
)

pytestmark = pytest.mark.integration

Uow = SqlAlchemyPersonalUnitOfWorkFactory
T0 = datetime(2026, 11, 1, 9, 0, tzinfo=UTC)


def _entity(scope: OwnerScope, name: str, kind: EntityType = EntityType.PERSON) -> Entity:
    return Entity(
        id=new_id(),
        owner_id=scope.owner_id,
        entity_type=kind,
        canonical_name=name,
        status=EntityStatus.ACTIVE,
    )


def _mention(scope: OwnerScope, source_id: uuid.UUID, text_: str) -> EntityMention:
    return EntityMention(
        id=new_id(),
        owner_id=scope.owner_id,
        source_id=source_id,
        mention_text=text_,
        mention_type=EntityType.PERSON,
        resolution_status=MentionResolutionStatus.UNRESOLVED,
        start_offset=0,
        end_offset=len(text_),
    )


def _record(
    scope: OwnerScope, outcome: EntityResolutionOutcome, **refs: Any
) -> EntityResolutionRecord:
    return EntityResolutionRecord(
        id=new_id(), owner_id=scope.owner_id, outcome=outcome, recorded_at=T0, **refs
    )


def _relationship(
    scope: OwnerScope, source: Entity, target: Entity, kind: EntityRelationshipType
) -> EntityRelationship:
    first, second = ordered_pair(source.id, target.id) if kind.symmetric else (source.id, target.id)
    return EntityRelationship(
        id=new_id(),
        owner_id=scope.owner_id,
        source_entity_id=first,
        target_entity_id=second,
        relationship_type=kind,
        origin_kind=ProvenanceOriginKind.EXPLICIT,
        recorded_at=T0,
        valid_from=T0,
        confidence=0.9,
    )


def _source(uow_factory: Uow, owner: OwnerScope, build: Any) -> Any:
    source = build.source(owner)
    with uow_factory() as uow:
        uow.sources.add(owner, source)
    return source


# --- entities, aliases and candidate lookup ----------------------------------------


def test_entity_and_alias_round_trip(uow_factory: Uow, owner: OwnerScope, build: Any) -> None:
    source = _source(uow_factory, owner, build)
    person = _entity(owner, "Synthetic Person")
    alias = EntityAlias(
        id=new_id(),
        owner_id=owner.owner_id,
        entity_id=person.id,
        alias="S. Person",
        source_id=source.id,
    )
    with uow_factory() as uow:
        uow.entities.add(owner, person)
        uow.entities.add_alias(owner, alias)

    with uow_factory() as uow:
        assert uow.entities.get(owner, person.id) == person
        assert uow.entities.list_aliases(owner, person.id) == [alias]


def test_alias_lookup_returns_candidates_not_identities(
    uow_factory: Uow, owner: OwnerScope, build: Any
) -> None:
    first = _entity(owner, "Alex Synthetic")
    second = _entity(owner, "Alexandra Example")
    with uow_factory() as uow:
        uow.entities.add(owner, first)
        uow.entities.add(owner, second)
        for target in (first, second):  # an ambiguous alias shared by two people
            uow.entities.add_alias(
                owner,
                EntityAlias(
                    id=new_id(), owner_id=owner.owner_id, entity_id=target.id, alias="Alex"
                ),
            )

    with uow_factory() as uow:
        assert {e.id for e in uow.entities.find_by_alias(owner, "  ALEX ")} == {first.id, second.id}
        assert [e.id for e in uow.entities.find_by_alias(owner, "alex synthetic")] == [first.id]
        assert uow.entities.find_by_alias(owner, "nobody") == []


def test_duplicate_alias_on_one_entity_is_rejected(uow_factory: Uow, owner: OwnerScope) -> None:
    person = _entity(owner, "Synthetic Person")
    with uow_factory() as uow:
        uow.entities.add(owner, person)
        uow.entities.add_alias(
            owner,
            EntityAlias(id=new_id(), owner_id=owner.owner_id, entity_id=person.id, alias="SP"),
        )
    with pytest.raises(PersistenceError) as caught, uow_factory() as uow:
        uow.entities.add_alias(
            owner,
            EntityAlias(id=new_id(), owner_id=owner.owner_id, entity_id=person.id, alias=" sp "),
        )
    assert caught.value.details["constraint"] == "uq_pm_entity_alias_entity_id_normalized_alias"


def test_shared_entities_are_rejected_by_the_database(
    connection: Connection, owner: OwnerScope
) -> None:
    savepoint = connection.begin_nested()
    with pytest.raises(IntegrityError, match="ck_pm_entity_private_only"):
        connection.execute(
            text(
                "INSERT INTO memory.pm_entity (id, owner_id, scope, entity_type, canonical_name,"
                " normalized_name, status) VALUES (:id, :owner, 'shared', 'product', 'X', 'x',"
                " 'active')"
            ),
            {"id": new_id(), "owner": owner.owner_id},
        )
    savepoint.rollback()


# --- mentions and resolution history -----------------------------------------------


def test_mention_resolution_keeps_wording_and_history(
    uow_factory: Uow, owner: OwnerScope, build: Any
) -> None:
    source = _source(uow_factory, owner, build)
    wrong, right = _entity(owner, "Wrong Person"), _entity(owner, "Right Person")
    mention = _mention(owner, source.id, "Dr. R. Person")
    with uow_factory() as uow:
        uow.entities.add(owner, wrong)
        uow.entities.add(owner, right)
        uow.mentions.add(owner, mention)
        uow.mentions.apply_resolution(
            owner,
            _record(
                owner,
                EntityResolutionOutcome.MATCHED_EXISTING,
                mention_id=mention.id,
                entity_id=wrong.id,
                candidate_entity_ids=(wrong.id, right.id),
                rationale="alias and context match",
            ),
            expected_status=MentionResolutionStatus.UNRESOLVED,
        )
        corrected = uow.mentions.apply_resolution(
            owner,
            _record(
                owner,
                EntityResolutionOutcome.CORRECTED,
                mention_id=mention.id,
                entity_id=right.id,
                previous_entity_id=wrong.id,
            ),
            expected_status=MentionResolutionStatus.RESOLVED,
        )

    assert corrected.entity_id == right.id
    assert corrected.mention_text == "Dr. R. Person"  # original wording preserved
    with uow_factory() as uow:
        history = uow.mentions.history(owner, mention_id=mention.id)
        assert [r.outcome for r in history] == [
            EntityResolutionOutcome.MATCHED_EXISTING,
            EntityResolutionOutcome.CORRECTED,
        ]
        assert history[0].candidate_entity_ids == (wrong.id, right.id)
        assert [m.id for m in uow.mentions.list_for_entity(owner, right.id)] == [mention.id]
        assert uow.mentions.list_for_entity(owner, wrong.id) == []


def test_uncertain_mentions_stay_unresolved_or_ambiguous(
    uow_factory: Uow, owner: OwnerScope, build: Any
) -> None:
    source = _source(uow_factory, owner, build)
    first, second = _entity(owner, "Alex One"), _entity(owner, "Alex Two")
    mention = _mention(owner, source.id, "Alex")
    with uow_factory() as uow:
        uow.entities.add(owner, first)
        uow.entities.add(owner, second)
        uow.mentions.add(owner, mention)
        ambiguous = uow.mentions.apply_resolution(
            owner,
            _record(
                owner,
                EntityResolutionOutcome.LEFT_UNRESOLVED,
                mention_id=mention.id,
                candidate_entity_ids=(first.id, second.id),
            ),
            expected_status=MentionResolutionStatus.UNRESOLVED,
        )
        review = uow.mentions.apply_resolution(
            owner,
            _record(owner, EntityResolutionOutcome.SENT_TO_REVIEW, mention_id=mention.id),
            expected_status=MentionResolutionStatus.AMBIGUOUS,
        )
    assert ambiguous.resolution_status is MentionResolutionStatus.AMBIGUOUS
    assert ambiguous.entity_id is None
    assert review.resolution_status is MentionResolutionStatus.NEEDS_REVIEW


def test_stale_or_mismatched_resolution_writes_nothing(
    uow_factory: Uow, owner: OwnerScope, build: Any
) -> None:
    source = _source(uow_factory, owner, build)
    person, other = _entity(owner, "Person A"), _entity(owner, "Person B")
    mention = _mention(owner, source.id, "A")
    with uow_factory() as uow:
        uow.entities.add(owner, person)
        uow.entities.add(owner, other)
        uow.mentions.add(owner, mention)

    match = _record(
        owner, EntityResolutionOutcome.MATCHED_EXISTING, mention_id=mention.id, entity_id=person.id
    )
    with pytest.raises(ConcurrencyConflictError), uow_factory() as uow:
        uow.mentions.apply_resolution(
            owner, match, expected_status=MentionResolutionStatus.RESOLVED
        )
    with uow_factory() as uow:
        uow.mentions.apply_resolution(
            owner, match, expected_status=MentionResolutionStatus.UNRESOLVED
        )
    # A correction must name the entity it actually replaces.
    wrong_previous = _record(
        owner,
        EntityResolutionOutcome.CORRECTED,
        mention_id=mention.id,
        entity_id=other.id,
        previous_entity_id=new_id(),
    )
    with pytest.raises(ConcurrencyConflictError), uow_factory() as uow:
        uow.mentions.apply_resolution(
            owner, wrong_previous, expected_status=MentionResolutionStatus.RESOLVED
        )
    with uow_factory() as uow:
        assert [r.id for r in uow.mentions.history(owner, mention_id=mention.id)] == [match.id]


# --- merges --------------------------------------------------------------------------


def test_merge_keeps_the_merged_entity_and_points_at_the_survivor(
    uow_factory: Uow, owner: OwnerScope, build: Any
) -> None:
    source = _source(uow_factory, owner, build)
    duplicate, survivor = (
        _entity(owner, "Company X Ltd", EntityType.ORGANIZATION),
        _entity(owner, "Company X", EntityType.ORGANIZATION),
    )
    mention = _mention(owner, source.id, "Company X Ltd")
    with uow_factory() as uow:
        uow.entities.add(owner, duplicate)
        uow.entities.add(owner, survivor)
        uow.mentions.add(owner, mention)
        uow.mentions.apply_resolution(
            owner,
            _record(
                owner,
                EntityResolutionOutcome.MATCHED_EXISTING,
                mention_id=mention.id,
                entity_id=duplicate.id,
            ),
            expected_status=MentionResolutionStatus.UNRESOLVED,
        )
        uow.entities.merge(
            owner,
            _record(
                owner,
                EntityResolutionOutcome.MERGED,
                entity_id=survivor.id,
                previous_entity_id=duplicate.id,
            ),
        )

    with uow_factory() as uow:
        merged = uow.entities.get(owner, duplicate.id)
        assert merged is not None and merged.status is EntityStatus.MERGED
        assert merged.merged_into_id == survivor.id
        assert uow.entities.canonical(owner, duplicate.id) == survivor
        # The mention still names the merged entity: the merge is correctable.
        assert [m.id for m in uow.mentions.list_for_entity(owner, duplicate.id)] == [mention.id]
        assert [r.outcome for r in uow.mentions.history(owner, entity_id=survivor.id)] == [
            EntityResolutionOutcome.MERGED
        ]
        # Merged entities take no new references and drop out of candidate lookup.
        assert uow.entities.find_by_alias(owner, "Company X Ltd") == []
        with pytest.raises(DomainValidationError, match="active"):
            uow.relationships.add_entity_relationship(
                owner, _relationship(owner, duplicate, survivor, EntityRelationshipType.RELATED_TO)
            )


def test_an_entity_cannot_be_merged_twice(uow_factory: Uow, owner: OwnerScope) -> None:
    a, b, c = (_entity(owner, name) for name in ("A", "B", "C"))
    with uow_factory() as uow:
        for item in (a, b, c):
            uow.entities.add(owner, item)
        uow.entities.merge(
            owner,
            _record(owner, EntityResolutionOutcome.MERGED, entity_id=b.id, previous_entity_id=a.id),
        )
    with pytest.raises(ConcurrencyConflictError), uow_factory() as uow:
        uow.entities.merge(
            owner,
            _record(owner, EntityResolutionOutcome.MERGED, entity_id=c.id, previous_entity_id=a.id),
        )


# --- relationships -------------------------------------------------------------------


def test_relationships_are_closed_and_replaced_not_overwritten(
    uow_factory: Uow, owner: OwnerScope
) -> None:
    person, old_job, new_job = (
        _entity(owner, "Synthetic Person"),
        _entity(owner, "Old Co", EntityType.ORGANIZATION),
        _entity(owner, "New Co", EntityType.ORGANIZATION),
    )
    old = _relationship(owner, person, old_job, EntityRelationshipType.WORKS_AT)
    new = _relationship(owner, person, new_job, EntityRelationshipType.WORKS_AT)
    moved_on = T0 + timedelta(days=30)
    with uow_factory() as uow:
        for item in (person, old_job, new_job):
            uow.entities.add(owner, item)
        uow.relationships.add_entity_relationship(owner, old)
        uow.relationships.close_entity_relationship(
            owner, old.id, valid_to=moved_on, superseded_at=moved_on
        )
        uow.relationships.add_entity_relationship(owner, new)

    with uow_factory() as uow:
        current = uow.relationships.entity_relationships(owner, person.id)
        everything = uow.relationships.entity_relationships(owner, person.id, include_history=True)
    assert [r.target_entity_id for r in current] == [new_job.id]
    assert {r.target_entity_id for r in everything} == {old_job.id, new_job.id}
    closed = next(r for r in everything if r.id == old.id)
    assert (closed.valid_to, closed.superseded_at) == (moved_on, moved_on)

    with pytest.raises(ConcurrencyConflictError), uow_factory() as uow:
        uow.relationships.close_entity_relationship(
            owner, old.id, valid_to=None, superseded_at=moved_on
        )


def test_one_current_relationship_per_pair_and_type(uow_factory: Uow, owner: OwnerScope) -> None:
    a, b = _entity(owner, "A"), _entity(owner, "B")
    with uow_factory() as uow:
        uow.entities.add(owner, a)
        uow.entities.add(owner, b)
        uow.relationships.add_entity_relationship(
            owner, _relationship(owner, a, b, EntityRelationshipType.KNOWS)
        )
    # The same symmetric fact from the other side is the same canonical row.
    with pytest.raises(PersistenceError) as caught, uow_factory() as uow:
        uow.relationships.add_entity_relationship(
            owner, _relationship(owner, b, a, EntityRelationshipType.KNOWS)
        )
    assert caught.value.details["constraint"] == "uq_pm_entity_relationship_current"


def test_symmetric_order_is_enforced_by_the_database(
    connection: Connection, uow_factory: Uow, owner: OwnerScope
) -> None:
    a, b = _entity(owner, "A"), _entity(owner, "B")
    with uow_factory() as uow:
        uow.entities.add(owner, a)
        uow.entities.add(owner, b)
    low, high = ordered_pair(a.id, b.id)
    savepoint = connection.begin_nested()
    with pytest.raises(IntegrityError, match="ck_pm_entity_relationship_symmetric_order"):
        connection.execute(
            text(
                "INSERT INTO memory.pm_entity_relationship (id, owner_id, source_entity_id,"
                " target_entity_id, relationship_type, origin_kind, recorded_at)"
                " VALUES (:id, :owner, :src, :tgt, 'knows', 'explicit', now())"
            ),
            {"id": new_id(), "owner": owner.owner_id, "src": high, "tgt": low},
        )
    savepoint.rollback()


def test_memory_relationships_and_associations(
    uow_factory: Uow, owner: OwnerScope, build: Any
) -> None:
    old, old_revision = build.memory(owner, "Synthetic user lives in City A.")
    new, new_revision = build.memory(owner, "Synthetic user lives in City B.")
    city = _entity(owner, "City B", EntityType.PLACE)
    supersedes = MemoryRelationship(
        id=new_id(),
        owner_id=owner.owner_id,
        source_memory_id=new.id,
        target_memory_id=old.id,
        relationship_type=MemoryRelationshipType.SUPERSEDES,
        reason=SupersessionReason.TEMPORAL_CHANGE,
        origin_kind=ProvenanceOriginKind.SYSTEM_GENERATED,
        recorded_at=T0,
    )
    association = MemoryEntityAssociation(
        id=new_id(),
        owner_id=owner.owner_id,
        memory_id=new.id,
        entity_id=city.id,
        role=MemoryEntityRole.OBJECT,
    )
    with uow_factory() as uow:
        uow.memories.add(owner, old, old_revision)
        uow.memories.add(owner, new, new_revision)
        uow.entities.add(owner, city)
        uow.relationships.add_memory_relationship(owner, supersedes)
        uow.relationships.associate(owner, association)

    with uow_factory() as uow:
        assert uow.relationships.memory_relationships(owner, old.id) == [supersedes]
        assert uow.relationships.entities_of_memory(owner, new.id) == [association]
        assert uow.relationships.memories_of_entity(owner, city.id) == [association]


def test_relationship_writes_respect_ownership(
    uow_factory: Uow, owner: OwnerScope, other_owner: OwnerScope, build: Any
) -> None:
    mine, theirs = _entity(owner, "Mine"), _entity(other_owner, "Theirs")
    with uow_factory() as uow:
        uow.entities.add(owner, mine)
        uow.entities.add(other_owner, theirs)

    cross = EntityRelationship(
        id=new_id(),
        owner_id=owner.owner_id,
        source_entity_id=mine.id,
        target_entity_id=theirs.id,
        relationship_type=EntityRelationshipType.WORKS_AT,
        origin_kind=ProvenanceOriginKind.EXPLICIT,
        recorded_at=T0,
    )
    with pytest.raises(RecordNotFoundError), uow_factory() as uow:
        uow.relationships.add_entity_relationship(owner, cross)
    with pytest.raises(OwnershipError), uow_factory() as uow:
        uow.entities.add(owner, _entity(other_owner, "Forged"))
    with uow_factory() as uow:
        assert uow.entities.get(other_owner, mine.id) is None
        assert uow.entities.find_by_alias(other_owner, "Mine") == []
        assert uow.relationships.entity_relationships(other_owner, mine.id) == []


def test_original_mention_wording_cannot_be_rewritten(
    connection: Connection, uow_factory: Uow, owner: OwnerScope, build: Any
) -> None:
    source = _source(uow_factory, owner, build)
    mention = _mention(owner, source.id, "Original wording")
    with uow_factory() as uow:
        uow.mentions.add(owner, mention)
    savepoint = connection.begin_nested()
    with pytest.raises(DBAPIError, match="immutable columns"):
        connection.execute(
            text("UPDATE memory.pm_entity_mention SET mention_text = 'rewritten' WHERE id = :id"),
            {"id": mention.id},
        )
    savepoint.rollback()
