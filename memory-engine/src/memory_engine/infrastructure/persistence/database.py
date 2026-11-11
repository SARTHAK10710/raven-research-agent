"""Engine, session factory and database-error translation.

One engine per process (Phase 7.1 section 23.2). Celery prefork children must
create their own engine after fork (Phase 8.3); never share one across fork.

Privacy: the engine is created with ``hide_parameters=True`` so SQLAlchemy
error messages never embed bound parameters, which can hold personal memory
content. Translated errors carry a fixed, safe message.
"""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import URL, Engine, create_engine
from sqlalchemy.exc import DBAPIError, IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from memory_engine.config.settings import DatabaseSettings
from memory_engine.exceptions import PersistenceError
from memory_engine.infrastructure.persistence.base import MEMORY_SCHEMA

DRIVER = "postgresql+psycopg"


def build_database_url(settings: DatabaseSettings) -> URL:
    """Build the SQLAlchemy URL. The password stays masked in ``str(url)``."""
    return URL.create(
        DRIVER,
        username=settings.user,
        password=settings.password.get_secret_value(),
        host=settings.host,
        port=settings.port,
        database=settings.name,
    )


def create_database_engine(settings: DatabaseSettings, *, url: URL | None = None) -> Engine:
    """Create the process-wide engine with pooling and safe defaults.

    ``url`` overrides the connection target (used by tests); pool, isolation and
    schema settings still come from ``settings``.
    """
    execution_options: dict[str, object] = {}
    if settings.schema_name != MEMORY_SCHEMA:
        execution_options["schema_translate_map"] = {MEMORY_SCHEMA: settings.schema_name}
    return create_engine(
        url if url is not None else build_database_url(settings),
        pool_size=settings.pool_size,
        max_overflow=settings.max_overflow,
        pool_recycle=settings.pool_recycle_seconds,
        pool_pre_ping=True,
        isolation_level="READ COMMITTED",
        hide_parameters=True,
        connect_args={"connect_timeout": settings.connect_timeout_seconds},
        execution_options=execution_options,
    )


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    # expire_on_commit=False: repositories return immutable domain objects, never
    # ORM instances, so nothing is lazily reloaded after commit.
    return sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)


@contextmanager
def translate_database_errors(operation: str) -> Iterator[None]:
    """Convert SQLAlchemy and driver errors into a safe :class:`PersistenceError`.

    ``operation`` is a short, fixed description such as ``"add atomic memory"``;
    it must never contain user data.
    """
    try:
        yield
    except IntegrityError as err:
        raise PersistenceError(
            f"Integrity constraint rejected: {operation}",
            details={"constraint": _constraint_name(err)},
        ) from err
    except DBAPIError as err:
        raise PersistenceError(f"Database operation failed: {operation}") from err
    except SQLAlchemyError as err:
        raise PersistenceError(f"Persistence layer error: {operation}") from err


def _constraint_name(err: IntegrityError) -> str:
    diag = getattr(err.orig, "diag", None)
    name = getattr(diag, "constraint_name", None)
    return name if isinstance(name, str) else "unknown"
