"""Domain invariants of episodes, profiles, categories and memory embeddings."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from memory_engine.domain.errors import DomainValidationError
from memory_engine.domain.identifiers import new_id
from memory_engine.domain.vocabulary import (
    EmbeddingPurpose,
    EmbeddingStatus,
    EpisodeStatus,
    MemoryCategory,
    MemoryOrigin,
    ProfileStatus,
    RefreshOutcome,
    RefreshTrigger,
    TemporalPrecision,
)
from memory_engine.personal.domain import (
    CategoryAssignment,
    Episode,
    EpisodeEvent,
    EpisodeMembership,
    MemoryEmbedding,
    ProfileRefresh,
    ProfileRevision,
    ProfileSupport,
)

T0 = datetime(2026, 11, 1, 9, 0, tzinfo=UTC)
OWNER = uuid.UUID("00000000-0000-4000-8000-000000000004")


def episode(**overrides: Any) -> Episode:
    values: dict[str, Any] = {
        "id": new_id(),
        "owner_id": OWNER,
        "status": EpisodeStatus.ACTIVE,
        "method": "episodic_formation",
        "method_version": "1",
        "recorded_at": T0,
    }
    return Episode(**{**values, **overrides})


def refresh(outcome: RefreshOutcome, **overrides: Any) -> ProfileRefresh:
    values: dict[str, Any] = {
        "id": new_id(),
        "owner_id": OWNER,
        "profile_id": new_id(),
        "trigger": RefreshTrigger.EVENT,
        "outcome": outcome,
        "from_revision": 1,
        "recorded_at": T0,
    }
    return ProfileRefresh(**{**values, **overrides})


# --- temporal precision ------------------------------------------------------------


def test_unknown_dates_are_never_fabricated() -> None:
    episode()  # both boundaries unknown
    episode(starts_at=T0, start_precision=TemporalPrecision.MONTH)
    with pytest.raises(DomainValidationError, match="starts_at"):
        episode(starts_at=T0)  # a date with 'unknown' precision
    with pytest.raises(DomainValidationError, match="ends_at"):
        episode(end_precision=TemporalPrecision.YEAR)  # known precision without a date


def test_episode_boundaries_are_ordered() -> None:
    with pytest.raises(DomainValidationError, match="end before"):
        episode(
            starts_at=T0,
            start_precision=TemporalPrecision.DAY,
            ends_at=T0 - timedelta(days=1),
            end_precision=TemporalPrecision.DAY,
        )


def test_timeline_events_follow_the_same_rule() -> None:
    base: dict[str, Any] = {
        "id": new_id(),
        "owner_id": OWNER,
        "episode_id": new_id(),
        "label": "Started the internship",
        "recorded_at": T0,
    }
    EpisodeEvent(**base, precision=TemporalPrecision.UNKNOWN)
    EpisodeEvent(**base, precision=TemporalPrecision.APPROXIMATE, occurred_at=T0)
    with pytest.raises(DomainValidationError):
        EpisodeEvent(**base, precision=TemporalPrecision.UNKNOWN, occurred_at=T0)
    with pytest.raises(DomainValidationError):
        EpisodeEvent(
            **base, precision=TemporalPrecision.UNKNOWN, superseded_at=T0 - timedelta(days=1)
        )


def test_membership_rules() -> None:
    base: dict[str, Any] = {
        "id": new_id(),
        "owner_id": OWNER,
        "episode_id": new_id(),
        "memory_id": new_id(),
        "added_at": T0,
    }
    EpisodeMembership(**base, sequence=0, confidence=0.7)
    for bad in ({"sequence": -1}, {"confidence": 1.1}, {"removed_at": T0 - timedelta(days=1)}):
        with pytest.raises(DomainValidationError):
            EpisodeMembership(**base, **bad)


# --- profiles ------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("outcome", "status"),
    [
        (RefreshOutcome.REFRESHED, ProfileStatus.CURRENT),
        (RefreshOutcome.NO_CHANGE, ProfileStatus.CURRENT),
        (RefreshOutcome.PARTIALLY_REFRESHED, ProfileStatus.STALE),
        (RefreshOutcome.FAILED, ProfileStatus.REFRESH_FAILED),
        (RefreshOutcome.NEEDS_REVIEW, ProfileStatus.NEEDS_REVIEW),
    ],
)
def test_partial_or_failed_refresh_never_leaves_a_profile_current(
    outcome: RefreshOutcome, status: ProfileStatus
) -> None:
    assert outcome.resulting_status() is status


def test_refresh_records_agree_with_their_outcome() -> None:
    refresh(RefreshOutcome.REFRESHED, to_revision=2)
    refresh(RefreshOutcome.NO_CHANGE)
    refresh(RefreshOutcome.FAILED, error_code="SOURCE_UNAVAILABLE")
    with pytest.raises(DomainValidationError, match="to_revision"):
        refresh(RefreshOutcome.REFRESHED)
    with pytest.raises(DomainValidationError, match="to_revision"):
        refresh(RefreshOutcome.NO_CHANGE, to_revision=2)
    with pytest.raises(DomainValidationError, match="next revision"):
        refresh(RefreshOutcome.REFRESHED, to_revision=3)
    with pytest.raises(DomainValidationError, match="failed"):
        refresh(RefreshOutcome.FAILED)
    with pytest.raises(DomainValidationError, match="UPPER_SNAKE_CASE"):
        refresh(RefreshOutcome.FAILED, error_code="the user's private note")


def test_profile_revisions_record_exact_memory_versions() -> None:
    support = ProfileSupport(
        memory_id=new_id(), memory_revision_number=3, attribute="theme", relevance=0.8
    )
    revision = ProfileRevision(
        id=new_id(),
        owner_id=OWNER,
        profile_id=new_id(),
        revision_number=1,
        method="profile_refresh",
        method_version="1",
        recorded_at=T0,
        attributes={"theme": "dark"},
        supports=(support,),
    )
    assert revision.supports == (support,)
    with pytest.raises(DomainValidationError):
        ProfileSupport(memory_id=new_id(), memory_revision_number=0)
    with pytest.raises(DomainValidationError):
        ProfileSupport(memory_id=new_id(), memory_revision_number=1, relevance=2.0)


# --- categories and embeddings -----------------------------------------------------------


def test_category_taxonomy_matches_5_4_9() -> None:
    assert len(MemoryCategory) == 8
    assignment = CategoryAssignment(
        id=new_id(),
        owner_id=OWNER,
        memory_id=new_id(),
        category=MemoryCategory.PERSONAL_PREFERENCE,
        origin=MemoryOrigin.INFERRED,
        recorded_at=T0,
        confidence=0.6,
    )
    assert assignment.superseded_at is None


def test_aspect_embeddings_and_only_they_carry_a_label() -> None:
    base: dict[str, Any] = {
        "id": new_id(),
        "owner_id": OWNER,
        "memory_id": new_id(),
        "revision_number": 1,
        "model_id": "synthetic-model",
        "model_revision": "r1",
        "dimensions": 384,
        "preprocessing_version": "p1",
        "status": EmbeddingStatus.PENDING,
    }
    MemoryEmbedding(**base, purpose=EmbeddingPurpose.PRIMARY)
    MemoryEmbedding(**base, purpose=EmbeddingPurpose.ASPECT, aspect_label="temporal")
    with pytest.raises(DomainValidationError):
        MemoryEmbedding(**base, purpose=EmbeddingPurpose.ASPECT)
    with pytest.raises(DomainValidationError):
        MemoryEmbedding(**base, purpose=EmbeddingPurpose.PRIMARY, aspect_label="x")
