"""Plan 8.2 step 4: episodes, profiles, categories and memory embeddings (real PostgreSQL).

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
    EmbeddingPurpose,
    EmbeddingStatus,
    EntityStatus,
    EntityType,
    EpisodeStatus,
    MemoryCategory,
    MemoryLifecycleStatus,
    MemoryOrigin,
    ProfileStatus,
    ProfileType,
    RefreshOutcome,
    RefreshTrigger,
    RevisionChangeType,
    TemporalPrecision,
)
from memory_engine.exceptions import (
    ConcurrencyConflictError,
    PersistenceError,
    RecordNotFoundError,
)
from memory_engine.infrastructure.persistence import SqlAlchemyPersonalUnitOfWorkFactory
from memory_engine.personal.domain import (
    CategoryAssignment,
    Entity,
    Episode,
    EpisodeEvent,
    EpisodeMembership,
    MemoryEmbedding,
    Profile,
    ProfileRefresh,
    ProfileRevision,
    ProfileSupport,
)

pytestmark = pytest.mark.integration

Uow = SqlAlchemyPersonalUnitOfWorkFactory
T0 = datetime(2026, 11, 1, 9, 0, tzinfo=UTC)


def _memory(uow_factory: Uow, owner: OwnerScope, build: Any, content: str) -> Any:
    memory, revision = build.memory(owner, content)
    with uow_factory() as uow:
        uow.memories.add(owner, memory, revision)
    return memory


def _episode(owner: OwnerScope, **overrides: Any) -> Episode:
    values: dict[str, Any] = {
        "id": new_id(),
        "owner_id": owner.owner_id,
        "status": EpisodeStatus.ACTIVE,
        "method": "episodic_formation",
        "method_version": "1",
        "recorded_at": T0,
        "title": "Synthetic internship",
    }
    return Episode(**{**values, **overrides})


def _membership(owner: OwnerScope, episode: Episode, memory: Any, sequence: int | None) -> Any:
    return EpisodeMembership(
        id=new_id(),
        owner_id=owner.owner_id,
        episode_id=episode.id,
        memory_id=memory.id,
        added_at=T0,
        sequence=sequence,
    )


def _profile_with_revision(
    owner: OwnerScope, supports: tuple[ProfileSupport, ...], **profile: Any
) -> tuple[Profile, ProfileRevision]:
    profile_id = new_id()
    values: dict[str, Any] = {
        "id": profile_id,
        "owner_id": owner.owner_id,
        "profile_type": ProfileType.PREFERENCE,
        "status": ProfileStatus.CURRENT,
        "revision_number": 1,
        "refreshed_at": T0,
    }
    revision = ProfileRevision(
        id=new_id(),
        owner_id=owner.owner_id,
        profile_id=profile_id,
        revision_number=1,
        method="profile_refresh",
        method_version="1",
        recorded_at=T0,
        attributes={"theme": "dark"},
        supports=supports,
    )
    return Profile(**{**values, **profile}), revision


def _next_revision(
    revision: ProfileRevision, supports: tuple[ProfileSupport, ...]
) -> ProfileRevision:
    return ProfileRevision(
        id=new_id(),
        owner_id=revision.owner_id,
        profile_id=revision.profile_id,
        revision_number=revision.revision_number + 1,
        method=revision.method,
        method_version=revision.method_version,
        recorded_at=revision.recorded_at + timedelta(days=1),
        attributes={"theme": "light"},
        supports=supports,
    )


def _refresh(
    owner: OwnerScope,
    profile_id: uuid.UUID,
    outcome: RefreshOutcome,
    from_revision: int,
    **extra: Any,
) -> ProfileRefresh:
    return ProfileRefresh(
        id=new_id(),
        owner_id=owner.owner_id,
        profile_id=profile_id,
        trigger=RefreshTrigger.EVENT,
        outcome=outcome,
        from_revision=from_revision,
        recorded_at=T0 + timedelta(days=from_revision),
        **extra,
    )


# --- episodes ------------------------------------------------------------------------


def test_episode_members_keep_order_and_removals_are_history(
    uow_factory: Uow, owner: OwnerScope, build: Any
) -> None:
    first = _memory(uow_factory, owner, build, "Started an internship.")
    second = _memory(uow_factory, owner, build, "Joined the mobile team.")
    loose = _memory(uow_factory, owner, build, "Received feedback.")
    episode = _episode(owner)
    with uow_factory() as uow:
        uow.episodes.add(owner, episode)
        uow.episodes.add_member(owner, _membership(owner, episode, loose, None))
        uow.episodes.add_member(owner, _membership(owner, episode, second, 1))
        removed = _membership(owner, episode, first, 0)
        uow.episodes.add_member(owner, removed)
        uow.episodes.remove_member(owner, removed.id, removed_at=T0 + timedelta(days=1))

    with uow_factory() as uow:
        current = uow.episodes.members(owner, episode.id)
        everything = uow.episodes.members(owner, episode.id, include_removed=True)
        assert [m.memory_id for m in current] == [second.id, loose.id]  # sequenced first
        assert {m.memory_id for m in everything} == {first.id, second.id, loose.id}
        assert [e.id for e in uow.episodes.episodes_of_memory(owner, second.id)] == [episode.id]
        assert uow.episodes.episodes_of_memory(owner, first.id) == []
        # The underlying memories are untouched by membership changes.
        assert uow.memories.get(owner, first.id) is not None


def test_a_memory_can_be_current_in_an_episode_only_once(
    uow_factory: Uow, owner: OwnerScope, build: Any
) -> None:
    memory = _memory(uow_factory, owner, build, "A fact.")
    episode = _episode(owner)
    with uow_factory() as uow:
        uow.episodes.add(owner, episode)
        uow.episodes.add_member(owner, _membership(owner, episode, memory, 0))
    with pytest.raises(PersistenceError) as caught, uow_factory() as uow:
        uow.episodes.add_member(owner, _membership(owner, episode, memory, 1))
    assert caught.value.details["constraint"] == "uq_pm_episode_membership_current"


def test_episode_updates_are_conditional(uow_factory: Uow, owner: OwnerScope) -> None:
    episode = _episode(owner)
    with uow_factory() as uow:
        uow.episodes.add(owner, episode)
        bounded = Episode(
            **{
                **{f: getattr(episode, f) for f in episode.__dataclass_fields__},
                "starts_at": T0,
                "start_precision": TemporalPrecision.MONTH,
                "status": EpisodeStatus.NEEDS_REFRESH,
            }
        )
        uow.episodes.update(owner, bounded, expected_status=EpisodeStatus.ACTIVE)
    with pytest.raises(ConcurrencyConflictError), uow_factory() as uow:
        uow.episodes.update(owner, episode, expected_status=EpisodeStatus.ACTIVE)
    with uow_factory() as uow:
        stored = uow.episodes.get(owner, episode.id)
    assert stored is not None
    assert (stored.status, stored.start_precision) == (
        EpisodeStatus.NEEDS_REFRESH,
        TemporalPrecision.MONTH,
    )


def test_timeline_corrections_keep_the_earlier_understanding(
    uow_factory: Uow, owner: OwnerScope
) -> None:
    episode = _episode(owner)
    wrong = EpisodeEvent(
        id=new_id(),
        owner_id=owner.owner_id,
        episode_id=episode.id,
        label="Internship started",
        precision=TemporalPrecision.DAY,
        occurred_at=T0,
        recorded_at=T0,
    )
    undated = EpisodeEvent(
        id=new_id(),
        owner_id=owner.owner_id,
        episode_id=episode.id,
        label="Feedback received",
        precision=TemporalPrecision.UNKNOWN,
        recorded_at=T0,
    )
    fixed = EpisodeEvent(
        id=new_id(),
        owner_id=owner.owner_id,
        episode_id=episode.id,
        label="Internship started",
        precision=TemporalPrecision.MONTH,
        occurred_at=T0 - timedelta(days=10),
        recorded_at=T0 + timedelta(days=2),
    )
    with uow_factory() as uow:
        uow.episodes.add(owner, episode)
        uow.episodes.add_event(owner, wrong)
        uow.episodes.add_event(owner, undated)
        uow.episodes.correct_event(owner, wrong.id, fixed)

    with uow_factory() as uow:
        current = uow.episodes.timeline(owner, episode.id)
        history = uow.episodes.timeline(owner, episode.id, include_history=True)
    assert [e.id for e in current] == [fixed.id, undated.id]  # undated events last
    closed = next(e for e in history if e.id == wrong.id)
    assert closed.superseded_at == fixed.recorded_at
    with pytest.raises(ConcurrencyConflictError), uow_factory() as uow:
        uow.episodes.correct_event(owner, wrong.id, fixed)


def test_fabricated_dates_are_rejected_by_the_database(
    connection: Connection, uow_factory: Uow, owner: OwnerScope
) -> None:
    episode = _episode(owner)
    with uow_factory() as uow:
        uow.episodes.add(owner, episode)
    savepoint = connection.begin_nested()
    with pytest.raises(IntegrityError, match="ck_pm_episode_event_occurred_known"):
        connection.execute(
            text(
                "INSERT INTO memory.pm_episode_event (id, owner_id, episode_id, label, occurred_at,"
                " precision, recorded_at) VALUES (:id, :owner, :ep, 'x', now(), 'unknown', now())"
            ),
            {"id": new_id(), "owner": owner.owner_id, "ep": episode.id},
        )
    savepoint.rollback()


# --- profiles ------------------------------------------------------------------------


def test_profile_refresh_creates_revisions_and_history(
    uow_factory: Uow, owner: OwnerScope, build: Any
) -> None:
    memory = _memory(uow_factory, owner, build, "Synthetic user prefers dark mode.")
    support = ProfileSupport(memory_id=memory.id, memory_revision_number=1, attribute="theme")
    profile, first = _profile_with_revision(owner, (support,))
    with uow_factory() as uow:
        uow.profiles.create(owner, profile, first)

    # The memory changes; the profile is refreshed from its new revision.
    with uow_factory() as uow:
        stored = uow.memories.get(owner, memory.id)
        assert stored is not None
        changed, change = build.next_state(
            stored, RevisionChangeType.UPDATED, content="Synthetic user prefers light mode."
        )
        uow.memories.apply_revision(owner, changed, change, expected_revision_number=1)
        second = _next_revision(
            first,
            (ProfileSupport(memory_id=memory.id, memory_revision_number=2, attribute="theme"),),
        )
        updated = uow.profiles.apply_refresh(
            owner,
            _refresh(owner, profile.id, RefreshOutcome.REFRESHED, 1, to_revision=2),
            expected_status=ProfileStatus.CURRENT,
            new_revision=second,
        )

    assert (updated.revision_number, updated.status) == (2, ProfileStatus.CURRENT)
    with uow_factory() as uow:
        current = uow.profiles.revision(owner, profile.id)
        original = uow.profiles.revision(owner, profile.id, 1)
        history = uow.profiles.history(owner, profile.id)
    assert current is not None and original is not None
    assert dict(current.attributes) == {"theme": "light"}
    assert dict(original.attributes) == {"theme": "dark"}  # previous content preserved
    assert original.supports[0].memory_revision_number == 1
    assert [h.outcome for h in history] == [RefreshOutcome.REFRESHED]


def test_failed_or_partial_refresh_never_leaves_a_profile_current(
    uow_factory: Uow, owner: OwnerScope, build: Any
) -> None:
    memory = _memory(uow_factory, owner, build, "A preference.")
    support = ProfileSupport(memory_id=memory.id, memory_revision_number=1)
    profile, first = _profile_with_revision(owner, (support,))
    with uow_factory() as uow:
        uow.profiles.create(owner, profile, first)
        failed = uow.profiles.apply_refresh(
            owner,
            _refresh(owner, profile.id, RefreshOutcome.FAILED, 1, error_code="SOURCE_TIMEOUT"),
            expected_status=ProfileStatus.CURRENT,
        )
        partial = uow.profiles.apply_refresh(
            owner,
            _refresh(owner, profile.id, RefreshOutcome.PARTIALLY_REFRESHED, 1, to_revision=2),
            expected_status=ProfileStatus.REFRESH_FAILED,
            new_revision=_next_revision(first, (support,)),
        )
    assert failed.status is ProfileStatus.REFRESH_FAILED
    assert (partial.status, partial.revision_number) == (ProfileStatus.STALE, 2)
    assert partial.refreshed_at == T0  # a partial refresh does not count as refreshed


def test_stale_refresh_writes_nothing(uow_factory: Uow, owner: OwnerScope, build: Any) -> None:
    memory = _memory(uow_factory, owner, build, "A preference.")
    support = ProfileSupport(memory_id=memory.id, memory_revision_number=1)
    profile, first = _profile_with_revision(owner, (support,))
    with uow_factory() as uow:
        uow.profiles.create(owner, profile, first)
        uow.profiles.apply_refresh(
            owner,
            _refresh(owner, profile.id, RefreshOutcome.REFRESHED, 1, to_revision=2),
            expected_status=ProfileStatus.CURRENT,
            new_revision=_next_revision(first, (support,)),
        )
    # A second worker that also started from revision 1 loses.
    with pytest.raises(PersistenceError), uow_factory() as uow:
        uow.profiles.apply_refresh(
            owner,
            _refresh(owner, profile.id, RefreshOutcome.REFRESHED, 1, to_revision=2),
            expected_status=ProfileStatus.CURRENT,
            new_revision=_next_revision(first, (support,)),
        )
    with pytest.raises(ConcurrencyConflictError), uow_factory() as uow:
        uow.profiles.apply_refresh(
            owner,
            _refresh(owner, profile.id, RefreshOutcome.NO_CHANGE, 1),
            expected_status=ProfileStatus.CURRENT,
        )
    with uow_factory() as uow:
        assert len(uow.profiles.history(owner, profile.id)) == 1


def test_profiles_cannot_cite_missing_memory_versions(
    uow_factory: Uow, owner: OwnerScope, other_owner: OwnerScope, build: Any
) -> None:
    mine = _memory(uow_factory, owner, build, "Mine.")
    theirs = _memory(uow_factory, other_owner, build, "Theirs.")
    for support in (
        ProfileSupport(memory_id=mine.id, memory_revision_number=7),  # no such revision
        ProfileSupport(memory_id=theirs.id, memory_revision_number=1),  # another owner
    ):
        profile, revision = _profile_with_revision(owner, (support,))
        with pytest.raises(RecordNotFoundError), uow_factory() as uow:
            uow.profiles.create(owner, profile, revision)


def test_one_live_profile_per_type_and_subject(
    uow_factory: Uow, owner: OwnerScope, build: Any
) -> None:
    project = Entity(
        id=new_id(),
        owner_id=owner.owner_id,
        entity_type=EntityType.PROJECT,
        canonical_name="Raven",
        status=EntityStatus.ACTIVE,
    )
    with uow_factory() as uow:
        uow.entities.add(owner, project)
        uow.profiles.create(owner, *_profile_with_revision(owner, ()))
        uow.profiles.create(
            owner,
            *_profile_with_revision(
                owner, (), profile_type=ProfileType.PROJECT, subject_entity_id=project.id
            ),
        )
    with pytest.raises(PersistenceError) as per_type, uow_factory() as uow:
        uow.profiles.create(owner, *_profile_with_revision(owner, ()))
    assert per_type.value.details["constraint"] == "uq_pm_profile_one_per_type"
    with pytest.raises(PersistenceError) as per_subject, uow_factory() as uow:
        uow.profiles.create(
            owner,
            *_profile_with_revision(
                owner, (), profile_type=ProfileType.PROJECT, subject_entity_id=project.id
            ),
        )
    assert per_subject.value.details["constraint"] == "uq_pm_profile_one_per_subject"


def test_supporting_memories_are_discoverable(
    uow_factory: Uow, owner: OwnerScope, build: Any
) -> None:
    memory = _memory(uow_factory, owner, build, "Supports a profile.")
    profile, revision = _profile_with_revision(
        owner, (ProfileSupport(memory_id=memory.id, memory_revision_number=1),)
    )
    with uow_factory() as uow:
        uow.profiles.create(owner, profile, revision)
        assert uow.profiles.profiles_supported_by(owner, memory.id) == [profile.id]
        # Refreshing without the memory drops it from the current revision.
        uow.profiles.apply_refresh(
            owner,
            _refresh(owner, profile.id, RefreshOutcome.REFRESHED, 1, to_revision=2),
            expected_status=ProfileStatus.CURRENT,
            new_revision=_next_revision(revision, ()),
        )
        assert uow.profiles.profiles_supported_by(owner, memory.id) == []


def test_profile_revisions_and_history_are_append_only(
    connection: Connection, uow_factory: Uow, owner: OwnerScope
) -> None:
    profile, revision = _profile_with_revision(owner, ())
    with uow_factory() as uow:
        uow.profiles.create(owner, profile, revision)
    savepoint = connection.begin_nested()
    with pytest.raises(DBAPIError, match="immutable columns"):
        connection.execute(
            text("UPDATE memory.pm_profile_revision SET attributes = '{}' WHERE profile_id = :p"),
            {"p": profile.id},
        )
    savepoint.rollback()


# --- categories and memory embeddings -----------------------------------------------


def test_category_changes_close_rather_than_overwrite(
    uow_factory: Uow, owner: OwnerScope, build: Any
) -> None:
    memory = _memory(uow_factory, owner, build, "I decided to use PostgreSQL.")
    first = CategoryAssignment(
        id=new_id(),
        owner_id=owner.owner_id,
        memory_id=memory.id,
        category=MemoryCategory.KNOWLEDGE,
        origin=MemoryOrigin.INFERRED,
        recorded_at=T0,
        confidence=0.4,
    )
    better = CategoryAssignment(
        id=new_id(),
        owner_id=owner.owner_id,
        memory_id=memory.id,
        category=MemoryCategory.DECISION,
        origin=MemoryOrigin.INFERRED,
        recorded_at=T0 + timedelta(days=1),
        confidence=0.9,
    )
    with uow_factory() as uow:
        uow.categories.assign(owner, first)
        uow.categories.close(owner, first.id, superseded_at=better.recorded_at)
        uow.categories.assign(owner, better)

    with uow_factory() as uow:
        assert [c.category for c in uow.categories.current(owner, memory.id)] == [
            MemoryCategory.DECISION
        ]
        assert len(uow.categories.history(owner, memory.id)) == 2
        assert uow.categories.memories_in(owner, MemoryCategory.DECISION) == [memory.id]
        assert uow.categories.memories_in(owner, MemoryCategory.KNOWLEDGE) == []


def test_categories_of_tombstoned_memories_are_not_listed(
    uow_factory: Uow, owner: OwnerScope, build: Any
) -> None:
    memory, created = build.memory(owner, "Soon forgotten.")
    with uow_factory() as uow:
        uow.memories.add(owner, memory, created)
        uow.categories.assign(
            owner,
            CategoryAssignment(
                id=new_id(),
                owner_id=owner.owner_id,
                memory_id=memory.id,
                category=MemoryCategory.GOAL,
                origin=MemoryOrigin.EXPLICIT,
                recorded_at=T0,
            ),
        )
        pending, rev = build.next_state(
            memory,
            RevisionChangeType.RETRACTED,
            lifecycle_status=MemoryLifecycleStatus.DELETION_PENDING,
        )
        uow.memories.apply_revision(owner, pending, rev, expected_revision_number=1)
        assert uow.categories.memories_in(owner, MemoryCategory.GOAL) == []


def test_memory_embeddings_are_per_revision_with_one_primary(
    uow_factory: Uow, owner: OwnerScope, build: Any
) -> None:
    memory = _memory(uow_factory, owner, build, "Embed me.")

    def embedding(**overrides: Any) -> MemoryEmbedding:
        values: dict[str, Any] = {
            "id": new_id(),
            "owner_id": owner.owner_id,
            "memory_id": memory.id,
            "revision_number": 1,
            "purpose": EmbeddingPurpose.PRIMARY,
            "model_id": "synthetic-model",
            "model_revision": "r1",
            "dimensions": 384,
            "preprocessing_version": "p1",
            "status": EmbeddingStatus.PENDING,
        }
        return MemoryEmbedding(**{**values, **overrides})

    primary = embedding()
    aspect = embedding(purpose=EmbeddingPurpose.ASPECT, aspect_label="temporal")
    with uow_factory() as uow:
        uow.memory_embeddings.add(owner, primary)
        uow.memory_embeddings.add(owner, aspect)
        uow.memory_embeddings.set_status(
            owner, primary.id, EmbeddingStatus.GENERATING, expected=EmbeddingStatus.PENDING
        )
        stored = uow.memory_embeddings.for_memory(owner, memory.id)
    assert [e.id for e in stored] == [primary.id, aspect.id]
    assert stored[0].status is EmbeddingStatus.GENERATING

    with pytest.raises(PersistenceError) as caught, uow_factory() as uow:
        uow.memory_embeddings.add(owner, embedding())
    assert caught.value.details["constraint"] == "uq_pm_memory_embedding_primary"
    with pytest.raises(RecordNotFoundError), uow_factory() as uow:
        uow.memory_embeddings.add(owner, embedding(revision_number=5))


def test_derived_records_respect_ownership(
    uow_factory: Uow, owner: OwnerScope, other_owner: OwnerScope, build: Any
) -> None:
    theirs = _memory(uow_factory, other_owner, build, "Theirs.")
    episode = _episode(owner)
    with uow_factory() as uow:
        uow.episodes.add(owner, episode)
    with pytest.raises(RecordNotFoundError), uow_factory() as uow:
        uow.episodes.add_member(owner, _membership(owner, episode, theirs, 0))
    with pytest.raises(RecordNotFoundError), uow_factory() as uow:
        uow.categories.assign(
            owner,
            CategoryAssignment(
                id=new_id(),
                owner_id=owner.owner_id,
                memory_id=theirs.id,
                category=MemoryCategory.GOAL,
                origin=MemoryOrigin.EXPLICIT,
                recorded_at=T0,
            ),
        )
    with pytest.raises(OwnershipError), uow_factory() as uow:
        uow.episodes.add(owner, _episode(other_owner))
    with uow_factory() as uow:
        assert uow.episodes.get(other_owner, episode.id) is None
        assert uow.episodes.members(other_owner, episode.id) == []


def test_refresh_outcome_and_revision_must_agree(uow_factory: Uow, owner: OwnerScope) -> None:
    profile, revision = _profile_with_revision(owner, ())
    with uow_factory() as uow:
        uow.profiles.create(owner, profile, revision)
    with pytest.raises(DomainValidationError), uow_factory() as uow:
        uow.profiles.apply_refresh(
            owner,
            _refresh(owner, profile.id, RefreshOutcome.REFRESHED, 1, to_revision=2),
            expected_status=ProfileStatus.CURRENT,
        )
