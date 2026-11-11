"""Unit of work: one short database transaction over Personal Memory records.

Commits when the ``with`` block completes normally, rolls back when it raises,
and always closes the session. An operation is never reported as successful
before the commit has succeeded (coding standards: error handling).
"""

from types import TracebackType
from typing import Self

from sqlalchemy.orm import Session, sessionmaker

from memory_engine.infrastructure.persistence.database import translate_database_errors
from memory_engine.infrastructure.persistence.personal.repositories import (
    SqlAlchemyAtomicMemoryRepository,
    SqlAlchemyMemoryCandidateRepository,
    SqlAlchemyMemorySourceRepository,
    SqlAlchemyProvenanceRepository,
)


class SqlAlchemyPersonalUnitOfWork:
    sources: SqlAlchemyMemorySourceRepository
    candidates: SqlAlchemyMemoryCandidateRepository
    memories: SqlAlchemyAtomicMemoryRepository
    provenance: SqlAlchemyProvenanceRepository

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self._session: Session | None = None

    def __enter__(self) -> Self:
        if self._session is not None:
            raise RuntimeError("unit of work is already active; create a new one per operation")
        session = self._session_factory()
        self._session = session
        self.sources = SqlAlchemyMemorySourceRepository(session)
        self.candidates = SqlAlchemyMemoryCandidateRepository(session, self.sources)
        self.memories = SqlAlchemyAtomicMemoryRepository(session)
        self.provenance = SqlAlchemyProvenanceRepository(
            session, self.sources, self.candidates, self.memories
        )
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        session = self._session
        self._session = None
        if session is None:
            return
        try:
            if exc_type is None:
                with translate_database_errors("commit unit of work"):
                    session.commit()
            else:
                session.rollback()
        except BaseException:
            session.rollback()
            raise
        finally:
            session.close()


class SqlAlchemyPersonalUnitOfWorkFactory:
    """Creates a fresh unit of work per operation (satisfies ``PersonalUnitOfWorkFactory``)."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def __call__(self) -> SqlAlchemyPersonalUnitOfWork:
        return SqlAlchemyPersonalUnitOfWork(self._session_factory)
