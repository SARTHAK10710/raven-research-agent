"""Persistence definitions that can be checked without a database.

* The migration's frozen vocabularies still equal the domain enums.
* The ORM models' check constraints are built from those same enums.
* Engine construction and error translation behave safely.
"""

import importlib.util
import re
from enum import StrEnum
from pathlib import Path
from types import ModuleType

import pytest
from pydantic import SecretStr
from sqlalchemy import CheckConstraint
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import sessionmaker

from memory_engine.config.settings import DatabaseSettings
from memory_engine.domain import vocabulary
from memory_engine.exceptions import PersistenceError
from memory_engine.infrastructure.persistence import (
    SqlAlchemyPersonalUnitOfWorkFactory,
    build_database_url,
    create_database_engine,
    translate_database_errors,
)
from memory_engine.infrastructure.persistence.base import Base
from memory_engine.infrastructure.persistence.personal import models
from memory_engine.personal.application.ports import (
    AtomicMemoryRepository,
    MemoryCandidateRepository,
    MemorySourceRepository,
    PersonalUnitOfWork,
    PersonalUnitOfWorkFactory,
    ProvenanceRepository,
)

MIGRATION = (
    Path(__file__).resolve().parents[3]
    / "memory-engine"
    / "migrations"
    / "versions"
    / "20261111_0001_personal_memory_core.py"
)
PASSWORD = "synthetic-db-password-91c2"  # noqa: S105 - test-only value


def _load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("migration_0001", MIGRATION)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("frozen_name", "enum"),
    [
        ("SOURCE_TYPES", vocabulary.SourceType),
        ("SOURCE_PROCESSING_STATUSES", vocabulary.SourceProcessingStatus),
        ("CANDIDATE_STATUSES", vocabulary.CandidateStatus),
        ("CANDIDATE_ORIGINS", vocabulary.CandidateOrigin),
        ("MEMORY_ORIGINS", vocabulary.MemoryOrigin),
        ("MEMORY_LIFECYCLE_STATUSES", vocabulary.MemoryLifecycleStatus),
        ("REVISION_CHANGE_TYPES", vocabulary.RevisionChangeType),
        ("PROVENANCE_ROLES", vocabulary.ProvenanceRole),
        ("PROVENANCE_ORIGIN_KINDS", vocabulary.ProvenanceOriginKind),
    ],
)
def test_migration_vocabularies_match_domain_enums(frozen_name: str, enum: type[StrEnum]) -> None:
    frozen = getattr(_load_migration(), frozen_name)
    assert tuple(frozen) == tuple(member.value for member in enum)


def test_migration_and_models_share_the_content_lifecycle_rule() -> None:
    assert _load_migration().CONTENT_MATCHES_LIFECYCLE == models.CONTENT_MATCHES_LIFECYCLE


VOCABULARIES = [
    value
    for value in vars(vocabulary).values()
    if isinstance(value, type) and issubclass(value, StrEnum) and value is not StrEnum
]


def test_vocabulary_module_defines_the_expected_enums() -> None:
    assert len(VOCABULARIES) == 12


def test_sqlalchemy_adapters_satisfy_the_application_ports() -> None:
    # Checked statically by mypy (structural typing) and at runtime by construction.
    session_factory = sessionmaker()
    factory: PersonalUnitOfWorkFactory = SqlAlchemyPersonalUnitOfWorkFactory(session_factory)
    unit: PersonalUnitOfWork = factory().__enter__()
    sources: MemorySourceRepository = unit.sources
    candidates: MemoryCandidateRepository = unit.candidates
    memories: AtomicMemoryRepository = unit.memories
    provenance: ProvenanceRepository = unit.provenance
    assert all(port is not None for port in (sources, candidates, memories, provenance))
    concrete = SqlAlchemyPersonalUnitOfWorkFactory(session_factory)()
    concrete.__enter__()
    with pytest.raises(RuntimeError, match="already active"):
        concrete.__enter__()
    concrete.__exit__(None, None, None)


@pytest.mark.parametrize("enum", VOCABULARIES, ids=lambda enum: enum.__name__)
def test_vocabulary_values_are_lowercase_snake_case(enum: type[StrEnum]) -> None:
    assert all(re.fullmatch(r"[a-z][a-z0-9_]*", member.value) for member in enum)


def test_every_pm_table_is_owner_scoped_with_prefix() -> None:
    tables = {t.name: t for t in Base.metadata.tables.values() if t.schema == "memory"}
    assert set(tables) == {
        "pm_memory_source",
        "pm_memory_candidate",
        "pm_atomic_memory",
        "pm_atomic_memory_revision",
        "pm_provenance",
    }
    for table in tables.values():
        assert table.c.owner_id.nullable is False


def test_foreign_keys_never_cascade_and_always_include_owner() -> None:
    for table in Base.metadata.tables.values():
        for fk in table.foreign_key_constraints:
            assert fk.ondelete == "RESTRICT", fk.name
            if fk.referred_table.name != "pm_atomic_memory_revision":
                assert "owner_id" in fk.column_keys, fk.name


def test_model_check_constraints_list_every_enum_value() -> None:
    lifecycle = next(
        c
        for c in Base.metadata.tables["memory.pm_atomic_memory"].constraints
        if isinstance(c, CheckConstraint) and c.name == "ck_pm_atomic_memory_lifecycle_status"
    )
    for status in vocabulary.MemoryLifecycleStatus:
        assert f"'{status.value}'" in str(lifecycle.sqltext)


def test_constraint_names_fit_postgresql_identifier_limit() -> None:
    for table in Base.metadata.tables.values():
        names = [c.name for c in table.constraints] + [i.name for i in table.indexes]
        for name in names:
            assert isinstance(name, str)
            assert len(name) <= 63, name


# --- engine and error translation -------------------------------------------------


def _settings(**overrides: object) -> DatabaseSettings:
    values: dict[str, object] = {
        "host": "db.test.invalid",
        "name": "raven_test",
        "user": "raven_memory_role",
        "password": SecretStr(PASSWORD),
    }
    return DatabaseSettings.model_validate({**values, **overrides})


def test_database_url_masks_the_password() -> None:
    url = build_database_url(_settings())
    assert url.drivername == "postgresql+psycopg"
    assert PASSWORD not in str(url)
    assert PASSWORD not in repr(url)
    assert url.password == PASSWORD


def test_engine_uses_safe_defaults_without_connecting() -> None:
    engine = create_database_engine(_settings(pool_size=3, max_overflow=1))
    try:
        assert engine.hide_parameters is True
        assert engine.pool.size() == 3  # type: ignore[attr-defined]
        assert "schema_translate_map" not in engine.get_execution_options()
    finally:
        engine.dispose()


def test_engine_maps_a_custom_schema_name() -> None:
    engine = create_database_engine(_settings(schema_name="memory_tenant_x"))
    try:
        assert engine.get_execution_options()["schema_translate_map"] == {
            "memory": "memory_tenant_x"
        }
    finally:
        engine.dispose()


class _Diag:
    constraint_name = "uq_example"


class _DriverError(Exception):
    diag = _Diag()


def test_integrity_errors_become_persistence_errors_with_constraint_name() -> None:
    with pytest.raises(PersistenceError) as caught, translate_database_errors("add example"):
        raise IntegrityError("INSERT ...", {"content": "private text"}, _DriverError())
    assert caught.value.details == {"constraint": "uq_example"}
    assert "private text" not in str(caught.value)
    assert isinstance(caught.value.__cause__, IntegrityError)


def test_connection_errors_become_persistence_errors() -> None:
    with (
        pytest.raises(PersistenceError, match="Database operation failed: get example"),
        translate_database_errors("get example"),
    ):
        raise OperationalError("SELECT 1", None, Exception("connection refused"))


def test_domain_errors_pass_through_untranslated() -> None:
    with pytest.raises(ValueError, match="kept"), translate_database_errors("noop"):
        raise ValueError("kept")
