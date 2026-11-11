"""Plan 8.2 section 13 failure tests that need real, separate transactions.

The other integration tests share one rolled-back connection, so their conflict
tests are sequential. Here two connections race for the same row, and a
migration fails part-way. These tests commit, so each one removes what it wrote.
"""

import threading
import time
from collections.abc import Callable, Iterator
from dataclasses import replace
from datetime import UTC, datetime

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Connection, Engine, inspect, text
from sqlalchemy.orm import sessionmaker

from memory_engine.domain.identifiers import OwnerScope, new_id
from memory_engine.domain.vocabulary import EpisodeStatus
from memory_engine.exceptions import ConcurrencyConflictError
from memory_engine.infrastructure.persistence import SqlAlchemyPersonalUnitOfWorkFactory
from memory_engine.personal.domain import Episode

pytestmark = pytest.mark.integration

T0 = datetime(2026, 11, 1, 9, 0, tzinfo=UTC)
FAILURE_SCHEMA = "memory_failure_check"


@pytest.fixture
def committed_owner(engine: Engine) -> Iterator[OwnerScope]:
    owner = OwnerScope(new_id())
    yield owner
    with engine.begin() as connection:
        connection.execute(
            text("DELETE FROM memory.pm_episode WHERE owner_id = :o"), {"o": owner.owner_id}
        )


def test_racing_transactions_cannot_both_update_an_episode(
    engine: Engine, committed_owner: OwnerScope
) -> None:
    owner = committed_owner
    factory = SqlAlchemyPersonalUnitOfWorkFactory(sessionmaker(bind=engine, expire_on_commit=False))
    episode = Episode(
        id=new_id(),
        owner_id=owner.owner_id,
        status=EpisodeStatus.ACTIVE,
        method="episodic_formation",
        method_version="1",
        recorded_at=T0,
        title="Synthetic project",
    )
    with factory() as uow:
        uow.episodes.add(owner, episode)

    first_holds_lock = threading.Event()
    outcome: list[BaseException | None] = []

    def second_writer() -> None:
        # Read version 1 like the first writer, then try to write after it.
        first_holds_lock.wait(timeout=10)
        try:
            with factory() as uow:
                uow.episodes.update(
                    owner, replace(episode, version=2, title="Second"), expected_version=1
                )
            outcome.append(None)
        except BaseException as err:  # recorded and asserted below
            outcome.append(err)

    thread = threading.Thread(target=second_writer)
    thread.start()
    with factory() as uow:
        uow.episodes.update(owner, replace(episode, version=2, title="First"), expected_version=1)
        first_holds_lock.set()
        # Keep the row lock long enough for the second writer to block on it.
        time.sleep(0.5)
    thread.join(timeout=10)

    assert not thread.is_alive()
    assert len(outcome) == 1 and isinstance(outcome[0], ConcurrencyConflictError)
    with factory() as uow:
        stored = uow.episodes.get(owner, episode.id)
    assert stored is not None and (stored.version, stored.title) == (2, "First")


def test_a_failing_migration_leaves_the_previous_revision_intact(
    engine: Engine,
    make_alembic_config: Callable[[Connection, str], Config],
    drop_schema: Callable[[Connection, str], None],
) -> None:
    try:
        with engine.begin() as connection:
            drop_schema(connection, FAILURE_SCHEMA)
            command.upgrade(
                make_alembic_config(connection, FAILURE_SCHEMA), "0004_episodes_profiles"
            )
            # A table in the way makes 0005 fail after it has created others.
            connection.execute(text(f'CREATE TABLE "{FAILURE_SCHEMA}".pm_deletion_target (x int)'))

        with pytest.raises(Exception, match="pm_deletion_target"), engine.begin() as connection:
            command.upgrade(make_alembic_config(connection, FAILURE_SCHEMA), "head")

        with engine.connect() as connection:
            version = connection.scalar(
                text(f'SELECT version_num FROM "{FAILURE_SCHEMA}".alembic_version')  # noqa: S608 - constant test schema
            )
        tables = set(inspect(engine).get_table_names(schema=FAILURE_SCHEMA))
        assert version == "0004_episodes_profiles"
        # Tables 0005 created before failing were rolled back with it.
        assert "pm_source_processing_event" not in tables
        assert "pm_episode" in tables
        columns = {c["name"] for c in inspect(engine).get_columns("pm_episode", FAILURE_SCHEMA)}
        assert "version" not in columns
    finally:
        with engine.begin() as connection:
            drop_schema(connection, FAILURE_SCHEMA)
