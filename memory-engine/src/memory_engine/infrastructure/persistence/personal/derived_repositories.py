"""SQLAlchemy implementations of the episode, profile, category and embedding ports.

Same contract as the other Personal Memory repositories: owner-scoped SQL,
scope checks before writes, domain records out, conditional updates for state
changes. Derived records only ever reference live (non-tombstoned) memories
when they are written.
"""

import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import exists, select, text, update
from sqlalchemy.orm import Session

from memory_engine.domain.errors import DomainValidationError, OwnershipError
from memory_engine.domain.identifiers import OwnerScope
from memory_engine.domain.vocabulary import (
    EmbeddingPurpose,
    EmbeddingStatus,
    EntityStatus,
    EpisodeStatus,
    MemoryCategory,
    MemoryLifecycleStatus,
    MemoryOrigin,
    ProfileStatus,
    ProfileType,
    RefreshOutcome,
    RefreshTrigger,
    TemporalPrecision,
)
from memory_engine.exceptions import RecordNotFoundError
from memory_engine.infrastructure.persistence.database import (
    conditional_update,
    translate_database_errors,
)
from memory_engine.infrastructure.persistence.personal.derived_models import (
    EpisodeEventRow,
    EpisodeMembershipRow,
    EpisodeRow,
    MemoryCategoryRow,
    MemoryEmbeddingRow,
    ProfileMemoryRow,
    ProfileRefreshRow,
    ProfileRevisionRow,
    ProfileRow,
)
from memory_engine.infrastructure.persistence.personal.entity_models import EntityRow
from memory_engine.infrastructure.persistence.personal.models import (
    AtomicMemoryRevisionRow,
    AtomicMemoryRow,
)
from memory_engine.personal.domain import (
    CategoryAssignment,
    Episode,
    EpisodeEvent,
    EpisodeMembership,
    MemoryEmbedding,
    Profile,
    ProfileRefresh,
    ProfileRevision,
    ProfileSupport,
)

_TOMBSTONED_MEMORY = (
    MemoryLifecycleStatus.DELETION_PENDING.value,
    MemoryLifecycleStatus.DELETED.value,
)


def _require_in_scope(scope: OwnerScope, *owner_ids: uuid.UUID) -> None:
    if not all(scope.owns(owner_id) for owner_id in owner_ids):
        raise OwnershipError("record owner does not match the operation's owner scope")


def _require_live_memory(session: Session, scope: OwnerScope, memory_id: uuid.UUID) -> None:
    if not session.scalar(
        select(
            exists().where(
                AtomicMemoryRow.id == memory_id,
                AtomicMemoryRow.owner_id == scope.owner_id,
                AtomicMemoryRow.lifecycle_status.not_in(_TOMBSTONED_MEMORY),
            )
        )
    ):
        raise RecordNotFoundError("atomic memory not found")


def _require_memory_revision(
    session: Session, scope: OwnerScope, memory_id: uuid.UUID, revision_number: int
) -> None:
    _require_live_memory(session, scope, memory_id)
    if not session.scalar(
        select(
            exists().where(
                AtomicMemoryRevisionRow.memory_id == memory_id,
                AtomicMemoryRevisionRow.owner_id == scope.owner_id,
                AtomicMemoryRevisionRow.revision_number == revision_number,
            )
        )
    ):
        raise RecordNotFoundError("atomic memory revision not found")


def _require_aware(value: datetime) -> None:
    if value.utcoffset() is None:
        raise DomainValidationError("timestamps must be timezone-aware")


# --- mapping -----------------------------------------------------------------------


def _episode(row: EpisodeRow) -> Episode:
    return Episode(
        id=row.id,
        owner_id=row.owner_id,
        status=EpisodeStatus(row.status),
        method=row.method,
        method_version=row.method_version,
        recorded_at=row.recorded_at,
        title=row.title,
        summary=row.summary,
        starts_at=row.starts_at,
        start_precision=TemporalPrecision(row.start_precision),
        ends_at=row.ends_at,
        end_precision=TemporalPrecision(row.end_precision),
    )


def _membership(row: EpisodeMembershipRow) -> EpisodeMembership:
    return EpisodeMembership(
        id=row.id,
        owner_id=row.owner_id,
        episode_id=row.episode_id,
        memory_id=row.memory_id,
        added_at=row.added_at,
        sequence=row.sequence,
        confidence=row.confidence,
        removed_at=row.removed_at,
    )


def _event(row: EpisodeEventRow) -> EpisodeEvent:
    return EpisodeEvent(
        id=row.id,
        owner_id=row.owner_id,
        episode_id=row.episode_id,
        label=row.label,
        precision=TemporalPrecision(row.precision),
        recorded_at=row.recorded_at,
        occurred_at=row.occurred_at,
        memory_id=row.memory_id,
        superseded_at=row.superseded_at,
    )


def _profile(row: ProfileRow) -> Profile:
    return Profile(
        id=row.id,
        owner_id=row.owner_id,
        profile_type=ProfileType(row.profile_type),
        status=ProfileStatus(row.status),
        revision_number=row.current_revision_number,
        refreshed_at=row.refreshed_at,
        subject_entity_id=row.subject_entity_id,
    )


def _refresh(row: ProfileRefreshRow) -> ProfileRefresh:
    return ProfileRefresh(
        id=row.id,
        owner_id=row.owner_id,
        profile_id=row.profile_id,
        trigger=RefreshTrigger(row.trigger),
        outcome=RefreshOutcome(row.outcome),
        from_revision=row.from_revision,
        recorded_at=row.recorded_at,
        to_revision=row.to_revision,
        error_code=row.error_code,
    )


def _category(row: MemoryCategoryRow) -> CategoryAssignment:
    return CategoryAssignment(
        id=row.id,
        owner_id=row.owner_id,
        memory_id=row.memory_id,
        category=MemoryCategory(row.category),
        origin=MemoryOrigin(row.origin),
        recorded_at=row.recorded_at,
        confidence=row.confidence,
        superseded_at=row.superseded_at,
    )


def _embedding(row: MemoryEmbeddingRow) -> MemoryEmbedding:
    return MemoryEmbedding(
        id=row.id,
        owner_id=row.owner_id,
        memory_id=row.memory_id,
        revision_number=row.revision_number,
        purpose=EmbeddingPurpose(row.purpose),
        model_id=row.model_id,
        model_revision=row.model_revision,
        dimensions=row.dimensions,
        preprocessing_version=row.preprocessing_version,
        status=EmbeddingStatus(row.status),
        aspect_label=row.aspect_label,
    )


# --- episodes ------------------------------------------------------------------------


def _episode_values(episode: Episode) -> dict[str, object]:
    return {
        "title": episode.title,
        "summary": episode.summary,
        "status": episode.status.value,
        "starts_at": episode.starts_at,
        "start_precision": episode.start_precision.value,
        "ends_at": episode.ends_at,
        "end_precision": episode.end_precision.value,
        "method_version": episode.method_version,
    }


class SqlAlchemyEpisodeRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, scope: OwnerScope, episode: Episode) -> None:
        _require_in_scope(scope, episode.owner_id)
        with translate_database_errors("add episode"):
            self._session.add(
                EpisodeRow(
                    id=episode.id,
                    owner_id=episode.owner_id,
                    method=episode.method,
                    recorded_at=episode.recorded_at,
                    **_episode_values(episode),
                )
            )
            self._session.flush()

    def get(self, scope: OwnerScope, episode_id: uuid.UUID) -> Episode | None:
        with translate_database_errors("get episode"):
            row = self._session.scalar(
                select(EpisodeRow)
                .where(
                    EpisodeRow.id == episode_id,
                    EpisodeRow.owner_id == scope.owner_id,
                    EpisodeRow.status != EpisodeStatus.DELETED.value,
                )
                .execution_options(populate_existing=True)
            )
        return None if row is None else _episode(row)

    def update(
        self, scope: OwnerScope, episode: Episode, *, expected_status: EpisodeStatus
    ) -> None:
        _require_in_scope(scope, episode.owner_id)
        with translate_database_errors("update episode"):
            conditional_update(
                self._session,
                update(EpisodeRow)
                .where(
                    EpisodeRow.id == episode.id,
                    EpisodeRow.owner_id == scope.owner_id,
                    EpisodeRow.status == expected_status.value,
                )
                .values(**_episode_values(episode)),
                exists=select(EpisodeRow.id)
                .where(EpisodeRow.id == episode.id, EpisodeRow.owner_id == scope.owner_id)
                .exists(),
                what="episode",
            )

    def add_member(self, scope: OwnerScope, membership: EpisodeMembership) -> None:
        _require_in_scope(scope, membership.owner_id)
        if membership.removed_at is not None:
            raise DomainValidationError("a new membership is current")
        with translate_database_errors("add episode member"):
            if self.get(scope, membership.episode_id) is None:
                raise RecordNotFoundError("episode not found")
            _require_live_memory(self._session, scope, membership.memory_id)
            self._session.add(
                EpisodeMembershipRow(
                    id=membership.id,
                    owner_id=membership.owner_id,
                    episode_id=membership.episode_id,
                    memory_id=membership.memory_id,
                    sequence=membership.sequence,
                    confidence=membership.confidence,
                    added_at=membership.added_at,
                )
            )
            self._session.flush()

    def remove_member(
        self, scope: OwnerScope, membership_id: uuid.UUID, *, removed_at: datetime
    ) -> None:
        _require_aware(removed_at)
        with translate_database_errors("remove episode member"):
            conditional_update(
                self._session,
                update(EpisodeMembershipRow)
                .where(
                    EpisodeMembershipRow.id == membership_id,
                    EpisodeMembershipRow.owner_id == scope.owner_id,
                    EpisodeMembershipRow.removed_at.is_(None),
                )
                .values(removed_at=removed_at),
                exists=select(EpisodeMembershipRow.id)
                .where(
                    EpisodeMembershipRow.id == membership_id,
                    EpisodeMembershipRow.owner_id == scope.owner_id,
                )
                .exists(),
                what="episode membership",
            )

    def members(
        self, scope: OwnerScope, episode_id: uuid.UUID, *, include_removed: bool = False
    ) -> Sequence[EpisodeMembership]:
        statement = select(EpisodeMembershipRow).where(
            EpisodeMembershipRow.owner_id == scope.owner_id,
            EpisodeMembershipRow.episode_id == episode_id,
        )
        if not include_removed:
            statement = statement.where(EpisodeMembershipRow.removed_at.is_(None))
        with translate_database_errors("list episode members"):
            rows = self._session.scalars(
                statement.order_by(
                    EpisodeMembershipRow.sequence.asc().nulls_last(),
                    EpisodeMembershipRow.added_at,
                    EpisodeMembershipRow.id,
                ).execution_options(populate_existing=True)
            ).all()
        return [_membership(row) for row in rows]

    def episodes_of_memory(self, scope: OwnerScope, memory_id: uuid.UUID) -> Sequence[Episode]:
        with translate_database_errors("list episodes of memory"):
            rows = self._session.scalars(
                select(EpisodeRow)
                .join(
                    EpisodeMembershipRow,
                    (EpisodeMembershipRow.episode_id == EpisodeRow.id)
                    & (EpisodeMembershipRow.owner_id == EpisodeRow.owner_id),
                )
                .where(
                    EpisodeRow.owner_id == scope.owner_id,
                    EpisodeRow.status != EpisodeStatus.DELETED.value,
                    EpisodeMembershipRow.memory_id == memory_id,
                    EpisodeMembershipRow.removed_at.is_(None),
                )
                .order_by(EpisodeRow.recorded_at, EpisodeRow.id)
            ).all()
        return [_episode(row) for row in rows]

    def add_event(self, scope: OwnerScope, event: EpisodeEvent) -> None:
        _require_in_scope(scope, event.owner_id)
        if event.superseded_at is not None:
            raise DomainValidationError("a new timeline event is current")
        with translate_database_errors("add episode event"):
            if self.get(scope, event.episode_id) is None:
                raise RecordNotFoundError("episode not found")
            if event.memory_id is not None:
                _require_live_memory(self._session, scope, event.memory_id)
            self._session.add(
                EpisodeEventRow(
                    id=event.id,
                    owner_id=event.owner_id,
                    episode_id=event.episode_id,
                    memory_id=event.memory_id,
                    label=event.label,
                    occurred_at=event.occurred_at,
                    precision=event.precision.value,
                    recorded_at=event.recorded_at,
                )
            )
            self._session.flush()

    def correct_event(
        self, scope: OwnerScope, event_id: uuid.UUID, correction: EpisodeEvent
    ) -> None:
        _require_in_scope(scope, correction.owner_id)
        with translate_database_errors("correct episode event"):
            episode_id = self._session.scalar(
                select(EpisodeEventRow.episode_id).where(
                    EpisodeEventRow.id == event_id, EpisodeEventRow.owner_id == scope.owner_id
                )
            )
            if episode_id is None:
                raise RecordNotFoundError("episode event not found")
            if episode_id != correction.episode_id:
                raise DomainValidationError("a correction stays in the same episode")
            conditional_update(
                self._session,
                update(EpisodeEventRow)
                .where(
                    EpisodeEventRow.id == event_id,
                    EpisodeEventRow.owner_id == scope.owner_id,
                    EpisodeEventRow.superseded_at.is_(None),
                )
                .values(superseded_at=correction.recorded_at),
                exists=select(EpisodeEventRow.id).where(EpisodeEventRow.id == event_id).exists(),
                what="episode event",
            )
        self.add_event(scope, correction)

    def timeline(
        self, scope: OwnerScope, episode_id: uuid.UUID, *, include_history: bool = False
    ) -> Sequence[EpisodeEvent]:
        statement = select(EpisodeEventRow).where(
            EpisodeEventRow.owner_id == scope.owner_id,
            EpisodeEventRow.episode_id == episode_id,
        )
        if not include_history:
            statement = statement.where(EpisodeEventRow.superseded_at.is_(None))
        with translate_database_errors("list episode timeline"):
            rows = self._session.scalars(
                statement.order_by(
                    EpisodeEventRow.occurred_at.asc().nulls_last(),
                    EpisodeEventRow.recorded_at,
                    EpisodeEventRow.id,
                ).execution_options(populate_existing=True)
            ).all()
        return [_event(row) for row in rows]


# --- profiles ------------------------------------------------------------------------


class SqlAlchemyProfileRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, scope: OwnerScope, profile: Profile, revision: ProfileRevision) -> None:
        _require_in_scope(scope, profile.owner_id, revision.owner_id)
        if revision.profile_id != profile.id or revision.revision_number != 1:
            raise DomainValidationError("a new profile starts with its revision 1")
        if profile.revision_number != 1:
            raise DomainValidationError("a new profile points at revision 1")
        with translate_database_errors("create profile"):
            self._defer_checks()
            if profile.subject_entity_id is not None:
                status = self._session.scalar(
                    select(EntityRow.status).where(
                        EntityRow.id == profile.subject_entity_id,
                        EntityRow.owner_id == scope.owner_id,
                    )
                )
                if status != EntityStatus.ACTIVE.value:
                    raise RecordNotFoundError("subject entity not found")
            self._check_supports(revision)
            self._session.add(
                ProfileRow(
                    id=profile.id,
                    owner_id=profile.owner_id,
                    profile_type=profile.profile_type.value,
                    subject_entity_id=profile.subject_entity_id,
                    status=profile.status.value,
                    current_revision_number=1,
                    refreshed_at=profile.refreshed_at,
                )
            )
            self._session.flush()
            self._add_revision(revision)
            self._check_deferred()

    def get(self, scope: OwnerScope, profile_id: uuid.UUID) -> Profile | None:
        with translate_database_errors("get profile"):
            row = self._session.scalar(
                select(ProfileRow)
                .where(
                    ProfileRow.id == profile_id,
                    ProfileRow.owner_id == scope.owner_id,
                    ProfileRow.status != ProfileStatus.DELETED.value,
                )
                .execution_options(populate_existing=True)
            )
        return None if row is None else _profile(row)

    def revision(
        self, scope: OwnerScope, profile_id: uuid.UUID, revision_number: int | None = None
    ) -> ProfileRevision | None:
        profile = self.get(scope, profile_id)
        if profile is None:
            return None
        number = profile.revision_number if revision_number is None else revision_number
        with translate_database_errors("get profile revision"):
            row = self._session.scalar(
                select(ProfileRevisionRow).where(
                    ProfileRevisionRow.profile_id == profile_id,
                    ProfileRevisionRow.owner_id == scope.owner_id,
                    ProfileRevisionRow.revision_number == number,
                )
            )
            if row is None:
                return None
            supports = self._session.scalars(
                select(ProfileMemoryRow)
                .where(
                    ProfileMemoryRow.profile_id == profile_id,
                    ProfileMemoryRow.revision_number == number,
                )
                .order_by(ProfileMemoryRow.created_at, ProfileMemoryRow.id)
            ).all()
        return ProfileRevision(
            id=row.id,
            owner_id=row.owner_id,
            profile_id=row.profile_id,
            revision_number=row.revision_number,
            method=row.method,
            method_version=row.method_version,
            recorded_at=row.recorded_at,
            attributes=row.attributes,
            supports=tuple(
                ProfileSupport(
                    memory_id=s.memory_id,
                    memory_revision_number=s.memory_revision_number,
                    attribute=s.attribute,
                    relevance=s.relevance,
                )
                for s in supports
            ),
        )

    def apply_refresh(
        self,
        scope: OwnerScope,
        refresh: ProfileRefresh,
        *,
        expected_status: ProfileStatus,
        new_revision: ProfileRevision | None = None,
    ) -> Profile:
        _require_in_scope(scope, refresh.owner_id)
        if refresh.outcome.creates_revision != (new_revision is not None):
            raise DomainValidationError(f"outcome '{refresh.outcome}' and new_revision disagree")
        if new_revision is not None:
            _require_in_scope(scope, new_revision.owner_id)
            if (
                new_revision.profile_id != refresh.profile_id
                or new_revision.revision_number != refresh.to_revision
            ):
                raise DomainValidationError("the new revision must be the refresh's to_revision")
        values: dict[str, object] = {"status": refresh.outcome.resulting_status().value}
        if new_revision is not None:
            values["current_revision_number"] = new_revision.revision_number
        if refresh.outcome in (RefreshOutcome.REFRESHED, RefreshOutcome.NO_CHANGE):
            values["refreshed_at"] = refresh.recorded_at
        with translate_database_errors("apply profile refresh"):
            self._defer_checks()
            if new_revision is not None:
                self._check_supports(new_revision)
                self._add_revision(new_revision)
            conditional_update(
                self._session,
                update(ProfileRow)
                .where(
                    ProfileRow.id == refresh.profile_id,
                    ProfileRow.owner_id == scope.owner_id,
                    ProfileRow.status == expected_status.value,
                    ProfileRow.current_revision_number == refresh.from_revision,
                )
                .values(**values),
                exists=select(ProfileRow.id)
                .where(
                    ProfileRow.id == refresh.profile_id,
                    ProfileRow.owner_id == scope.owner_id,
                    ProfileRow.status != ProfileStatus.DELETED.value,
                )
                .exists(),
                what="profile",
            )
            self._session.add(
                ProfileRefreshRow(
                    id=refresh.id,
                    owner_id=refresh.owner_id,
                    profile_id=refresh.profile_id,
                    trigger=refresh.trigger.value,
                    outcome=refresh.outcome.value,
                    from_revision=refresh.from_revision,
                    to_revision=refresh.to_revision,
                    error_code=refresh.error_code,
                    recorded_at=refresh.recorded_at,
                )
            )
            self._session.flush()
            self._check_deferred()
        updated = self.get(scope, refresh.profile_id)
        if updated is None:  # pragma: no cover - updated in this transaction
            raise RecordNotFoundError("profile not found")
        return updated

    def history(self, scope: OwnerScope, profile_id: uuid.UUID) -> Sequence[ProfileRefresh]:
        with translate_database_errors("list profile refresh history"):
            rows = self._session.scalars(
                select(ProfileRefreshRow)
                .where(
                    ProfileRefreshRow.owner_id == scope.owner_id,
                    ProfileRefreshRow.profile_id == profile_id,
                )
                .order_by(ProfileRefreshRow.recorded_at, ProfileRefreshRow.seq)
            ).all()
        return [_refresh(row) for row in rows]

    def profiles_supported_by(self, scope: OwnerScope, memory_id: uuid.UUID) -> Sequence[uuid.UUID]:
        with translate_database_errors("find profiles supported by a memory"):
            return list(
                self._session.scalars(
                    select(ProfileRow.id)
                    .join(
                        ProfileMemoryRow,
                        (ProfileMemoryRow.profile_id == ProfileRow.id)
                        & (ProfileMemoryRow.revision_number == ProfileRow.current_revision_number),
                    )
                    .where(
                        ProfileRow.owner_id == scope.owner_id,
                        ProfileRow.status != ProfileStatus.DELETED.value,
                        ProfileMemoryRow.memory_id == memory_id,
                    )
                    .distinct()
                    .order_by(ProfileRow.id)
                ).all()
            )

    def _check_supports(self, revision: ProfileRevision) -> None:
        scope = OwnerScope(revision.owner_id)
        for support in revision.supports:
            _require_memory_revision(
                self._session, scope, support.memory_id, support.memory_revision_number
            )

    def _add_revision(self, revision: ProfileRevision) -> None:
        self._session.add(
            ProfileRevisionRow(
                id=revision.id,
                owner_id=revision.owner_id,
                profile_id=revision.profile_id,
                revision_number=revision.revision_number,
                attributes=dict(revision.attributes),
                method=revision.method,
                method_version=revision.method_version,
                recorded_at=revision.recorded_at,
            )
        )
        self._session.flush()
        for support in revision.supports:
            self._session.add(
                ProfileMemoryRow(
                    id=uuid.uuid4(),
                    owner_id=revision.owner_id,
                    profile_id=revision.profile_id,
                    revision_number=revision.revision_number,
                    memory_id=support.memory_id,
                    memory_revision_number=support.memory_revision_number,
                    attribute=support.attribute,
                    relevance=support.relevance,
                )
            )
        self._session.flush()

    def _defer_checks(self) -> None:
        # The profile <-> current-revision key is deferrable (the rows reference
        # each other). Defer it while this write inserts both rows...
        self._session.execute(text("SET CONSTRAINTS ALL DEFERRED"))

    def _check_deferred(self) -> None:
        # ...then check it now, inside the unit of work, rather than at commit.
        # SET CONSTRAINTS lasts for the transaction, so every profile write defers
        # again first; otherwise a second write in the same unit of work would be
        # checked before its revision exists (a test caught this).
        self._session.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))


# --- categories ----------------------------------------------------------------------


class SqlAlchemyCategoryRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def assign(self, scope: OwnerScope, assignment: CategoryAssignment) -> None:
        _require_in_scope(scope, assignment.owner_id)
        if assignment.superseded_at is not None:
            raise DomainValidationError("a new category assignment is current")
        with translate_database_errors("assign memory category"):
            _require_live_memory(self._session, scope, assignment.memory_id)
            self._session.add(
                MemoryCategoryRow(
                    id=assignment.id,
                    owner_id=assignment.owner_id,
                    memory_id=assignment.memory_id,
                    category=assignment.category.value,
                    origin=assignment.origin.value,
                    confidence=assignment.confidence,
                    recorded_at=assignment.recorded_at,
                )
            )
            self._session.flush()

    def close(
        self, scope: OwnerScope, assignment_id: uuid.UUID, *, superseded_at: datetime
    ) -> None:
        _require_aware(superseded_at)
        with translate_database_errors("close memory category"):
            conditional_update(
                self._session,
                update(MemoryCategoryRow)
                .where(
                    MemoryCategoryRow.id == assignment_id,
                    MemoryCategoryRow.owner_id == scope.owner_id,
                    MemoryCategoryRow.superseded_at.is_(None),
                )
                .values(superseded_at=superseded_at),
                exists=select(MemoryCategoryRow.id)
                .where(
                    MemoryCategoryRow.id == assignment_id,
                    MemoryCategoryRow.owner_id == scope.owner_id,
                )
                .exists(),
                what="category assignment",
            )

    def current(self, scope: OwnerScope, memory_id: uuid.UUID) -> Sequence[CategoryAssignment]:
        return self._list(scope, memory_id, current_only=True)

    def history(self, scope: OwnerScope, memory_id: uuid.UUID) -> Sequence[CategoryAssignment]:
        return self._list(scope, memory_id, current_only=False)

    def memories_in(self, scope: OwnerScope, category: MemoryCategory) -> Sequence[uuid.UUID]:
        with translate_database_errors("list memories in category"):
            return list(
                self._session.scalars(
                    select(MemoryCategoryRow.memory_id)
                    .join(
                        AtomicMemoryRow,
                        (AtomicMemoryRow.id == MemoryCategoryRow.memory_id)
                        & (AtomicMemoryRow.owner_id == MemoryCategoryRow.owner_id),
                    )
                    .where(
                        MemoryCategoryRow.owner_id == scope.owner_id,
                        MemoryCategoryRow.category == category.value,
                        MemoryCategoryRow.superseded_at.is_(None),
                        AtomicMemoryRow.lifecycle_status == MemoryLifecycleStatus.ACTIVE.value,
                    )
                    .order_by(MemoryCategoryRow.memory_id)
                ).all()
            )

    def _list(
        self, scope: OwnerScope, memory_id: uuid.UUID, *, current_only: bool
    ) -> Sequence[CategoryAssignment]:
        statement = select(MemoryCategoryRow).where(
            MemoryCategoryRow.owner_id == scope.owner_id,
            MemoryCategoryRow.memory_id == memory_id,
        )
        if current_only:
            statement = statement.where(MemoryCategoryRow.superseded_at.is_(None))
        with translate_database_errors("list memory categories"):
            rows = self._session.scalars(
                statement.order_by(
                    MemoryCategoryRow.recorded_at, MemoryCategoryRow.id
                ).execution_options(populate_existing=True)
            ).all()
        return [_category(row) for row in rows]


# --- memory embedding metadata -----------------------------------------------------


class SqlAlchemyMemoryEmbeddingRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, scope: OwnerScope, embedding: MemoryEmbedding) -> None:
        _require_in_scope(scope, embedding.owner_id)
        with translate_database_errors("add memory embedding"):
            _require_memory_revision(
                self._session, scope, embedding.memory_id, embedding.revision_number
            )
            self._session.add(
                MemoryEmbeddingRow(
                    id=embedding.id,
                    owner_id=embedding.owner_id,
                    memory_id=embedding.memory_id,
                    revision_number=embedding.revision_number,
                    purpose=embedding.purpose.value,
                    aspect_label=embedding.aspect_label,
                    model_id=embedding.model_id,
                    model_revision=embedding.model_revision,
                    dimensions=embedding.dimensions,
                    preprocessing_version=embedding.preprocessing_version,
                    status=embedding.status.value,
                )
            )
            self._session.flush()

    def set_status(
        self,
        scope: OwnerScope,
        embedding_id: uuid.UUID,
        status: EmbeddingStatus,
        *,
        expected: EmbeddingStatus,
    ) -> None:
        with translate_database_errors("set memory embedding status"):
            conditional_update(
                self._session,
                update(MemoryEmbeddingRow)
                .where(
                    MemoryEmbeddingRow.id == embedding_id,
                    MemoryEmbeddingRow.owner_id == scope.owner_id,
                    MemoryEmbeddingRow.status == expected.value,
                )
                .values(status=status.value),
                exists=select(MemoryEmbeddingRow.id)
                .where(
                    MemoryEmbeddingRow.id == embedding_id,
                    MemoryEmbeddingRow.owner_id == scope.owner_id,
                )
                .exists(),
                what="memory embedding",
            )

    def for_memory(self, scope: OwnerScope, memory_id: uuid.UUID) -> Sequence[MemoryEmbedding]:
        with translate_database_errors("list memory embeddings"):
            rows = self._session.scalars(
                select(MemoryEmbeddingRow)
                .where(
                    MemoryEmbeddingRow.owner_id == scope.owner_id,
                    MemoryEmbeddingRow.memory_id == memory_id,
                )
                .order_by(
                    MemoryEmbeddingRow.revision_number,
                    MemoryEmbeddingRow.purpose.desc(),  # 'primary' before 'aspect'
                    MemoryEmbeddingRow.created_at,
                    MemoryEmbeddingRow.id,
                )
                .execution_options(populate_existing=True)
            ).all()
        return [_embedding(row) for row in rows]
