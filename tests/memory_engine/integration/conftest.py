"""Fixtures for integration tests against a real PostgreSQL with pgvector.

Start the database with ``docker compose up -d postgres-test`` (repository root).
Override the target with ``RAVEN_TEST_DATABASE_URL``. As a safety guard, the
database name must end in ``_test``: these fixtures drop and recreate schemas.

Each test runs inside an outer transaction that is rolled back afterwards; a
unit of work's commit only releases a savepoint, so tests never leak data.
"""

import os
import uuid
from collections.abc import Callable, Iterator
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from pydantic import SecretStr
from sqlalchemy import Connection, Engine, make_url, text
from sqlalchemy.engine import URL
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from memory_engine.config.settings import DatabaseSettings
from memory_engine.domain.identifiers import OwnerScope, new_id
from memory_engine.domain.vocabulary import (
    CandidateOrigin,
    CandidateStatus,
    MemoryLifecycleStatus,
    MemoryOrigin,
    ProvenanceOriginKind,
    ProvenanceRole,
    RevisionChangeType,
    SourceProcessingStatus,
    SourceType,
)
from memory_engine.infrastructure.persistence import (
    SqlAlchemyPersonalUnitOfWorkFactory,
    create_database_engine,
)
from memory_engine.personal.domain import (
    AtomicMemory,
    AtomicMemoryRevision,
    MemoryCandidate,
    MemorySource,
    ProvenanceRecord,
)

DEFAULT_TEST_URL = (
    "postgresql+psycopg://raven_test:raven_test_only@127.0.0.1:55432/raven_memory_test"
)
REPO_ROOT = Path(__file__).resolve().parents[3]
ALEMBIC_INI = REPO_ROOT / "memory-engine" / "alembic.ini"
TEST_SCHEMA = "memory"


def _test_url() -> URL:
    url = make_url(os.environ.get("RAVEN_TEST_DATABASE_URL", DEFAULT_TEST_URL))
    if not (url.database or "").endswith("_test"):
        raise RuntimeError("Integration tests only run against a database whose name ends in _test")
    return url


def _settings(url: URL) -> DatabaseSettings:
    return DatabaseSettings(
        host=url.host or "127.0.0.1",
        port=url.port or 5432,
        name=url.database or "",
        user=url.username or "",
        password=SecretStr(url.password or "unused"),
        schema_name=TEST_SCHEMA,
        pool_size=2,
        max_overflow=0,
        connect_timeout_seconds=3,
    )


def alembic_config(connection: Connection, schema: str) -> Config:
    config = Config(str(ALEMBIC_INI))
    config.attributes["connection"] = connection
    config.attributes["memory_schema"] = schema
    return config


def reset_schema(connection: Connection, schema: str) -> None:
    connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))


@pytest.fixture
def make_alembic_config() -> Callable[[Connection, str], Config]:
    return alembic_config


@pytest.fixture
def drop_schema() -> Callable[[Connection, str], None]:
    return reset_schema


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    url = _test_url()
    engine = create_database_engine(_settings(url), url=url)
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except OperationalError:
        engine.dispose()
        pytest.skip(
            "PostgreSQL test database unreachable; run `docker compose up -d postgres-test`"
        )
    with engine.begin() as connection:
        reset_schema(connection, TEST_SCHEMA)
        command.upgrade(alembic_config(connection, TEST_SCHEMA), "head")
    yield engine
    engine.dispose()


@pytest.fixture
def connection(engine: Engine) -> Iterator[Connection]:
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            yield connection
        finally:
            transaction.rollback()


@pytest.fixture
def session_factory(connection: Connection) -> sessionmaker[Session]:
    return sessionmaker(
        bind=connection,
        expire_on_commit=False,
        autoflush=False,
        join_transaction_mode="create_savepoint",
    )


@pytest.fixture
def uow_factory(session_factory: sessionmaker[Session]) -> SqlAlchemyPersonalUnitOfWorkFactory:
    return SqlAlchemyPersonalUnitOfWorkFactory(session_factory)


@pytest.fixture
def owner() -> OwnerScope:
    return OwnerScope(uuid.uuid4())


@pytest.fixture
def other_owner() -> OwnerScope:
    return OwnerScope(uuid.uuid4())


T0 = datetime(2026, 11, 1, 9, 0, tzinfo=UTC)


class Builders:
    """Synthetic Personal Memory records for tests. No real user data."""

    def source(self, scope: OwnerScope) -> MemorySource:
        return MemorySource(
            id=new_id(),
            owner_id=scope.owner_id,
            source_type=SourceType.TEXT,
            processing_status=SourceProcessingStatus.EXTRACTED,
            received_at=T0,
            content_sha256="a" * 64,
        )

    def candidate(self, scope: OwnerScope, source_id: uuid.UUID) -> MemoryCandidate:
        return MemoryCandidate(
            id=new_id(),
            owner_id=scope.owner_id,
            source_id=source_id,
            proposition="Synthetic user prefers dark mode.",
            status=CandidateStatus.VALIDATED,
            origin=CandidateOrigin.EXPLICIT,
            importance=0.4,
            confidence=0.9,
            extraction_confidence=0.8,
            context={"scope": "ui"},
        )

    def memory(
        self, scope: OwnerScope, content: str = "Synthetic user prefers dark mode."
    ) -> tuple[AtomicMemory, AtomicMemoryRevision]:
        memory = AtomicMemory(
            id=new_id(),
            owner_id=scope.owner_id,
            content=content,
            origin=MemoryOrigin.EXPLICIT,
            lifecycle_status=MemoryLifecycleStatus.ACTIVE,
            recorded_at=T0,
            revision_number=1,
            structured={"attribute": "theme", "value": "dark"},
            importance=0.4,
            confidence=0.9,
            valid_from=T0,
            observed_at=T0,
        )
        revision = AtomicMemoryRevision.snapshot(
            memory, revision_id=new_id(), change_type=RevisionChangeType.CREATED
        )
        return memory, revision

    def next_state(
        self, memory: AtomicMemory, change_type: RevisionChangeType, **changes: object
    ) -> tuple[AtomicMemory, AtomicMemoryRevision]:
        updated = replace(
            memory,
            revision_number=memory.revision_number + 1,
            recorded_at=memory.recorded_at + timedelta(days=1),
            **changes,  # type: ignore[arg-type]
        )
        revision = AtomicMemoryRevision.snapshot(
            updated, revision_id=new_id(), change_type=change_type
        )
        return updated, revision

    def provenance(
        self,
        scope: OwnerScope,
        memory_id: uuid.UUID,
        *,
        source_id: uuid.UUID | None = None,
        candidate_id: uuid.UUID | None = None,
        revision_number: int | None = 1,
    ) -> ProvenanceRecord:
        return ProvenanceRecord(
            id=new_id(),
            owner_id=scope.owner_id,
            memory_id=memory_id,
            role=ProvenanceRole.ORIGIN,
            origin_kind=ProvenanceOriginKind.EXPLICIT,
            recorded_at=T0,
            source_id=source_id,
            candidate_id=candidate_id,
            revision_number=revision_number,
        )


@pytest.fixture
def build() -> Builders:
    return Builders()
