"""Plan 8.2 database tests: migration execution, reversibility and model agreement."""

from collections.abc import Callable

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import Connection, Engine, inspect, text

from memory_engine.infrastructure.persistence.base import Base
from memory_engine.infrastructure.persistence.personal import models

pytestmark = pytest.mark.integration

CHECK_SCHEMA = "memory_migration_check"
PM_TABLES = {
    "pm_memory_source",
    "pm_memory_candidate",
    "pm_atomic_memory",
    "pm_atomic_memory_revision",
    "pm_provenance",
}


def _tables(engine: Engine, schema: str) -> set[str]:
    return set(inspect(engine).get_table_names(schema=schema))


def test_upgrade_downgrade_upgrade_round_trip(
    engine: Engine,
    make_alembic_config: Callable[[Connection, str], Config],
    drop_schema: Callable[[Connection, str], None],
) -> None:
    try:
        with engine.begin() as connection:
            drop_schema(connection, CHECK_SCHEMA)
            command.upgrade(make_alembic_config(connection, CHECK_SCHEMA), "head")
        assert _tables(engine, CHECK_SCHEMA) >= PM_TABLES

        with engine.begin() as connection:
            command.downgrade(make_alembic_config(connection, CHECK_SCHEMA), "base")
        assert _tables(engine, CHECK_SCHEMA) == {"alembic_version"}

        with engine.begin() as connection:
            command.upgrade(make_alembic_config(connection, CHECK_SCHEMA), "head")
        assert _tables(engine, CHECK_SCHEMA) >= PM_TABLES
    finally:
        with engine.begin() as connection:
            drop_schema(connection, CHECK_SCHEMA)


def test_migrated_schema_matches_the_orm_models(engine: Engine) -> None:
    assert models.MemorySourceRow.__table__.schema == "memory"
    with engine.connect() as connection:
        context = MigrationContext.configure(
            connection, opts={"include_schemas": True, "include_name": _only_memory_schema}
        )
        differences = compare_metadata(context, Base.metadata)
    assert differences == []


def test_deployed_constraint_names_equal_the_model_names(engine: Engine) -> None:
    # compare_metadata does not compare check constraints or constraint names, and
    # error handling and tests rely on these names, so compare them explicitly.
    expected = {
        constraint.name
        for table in Base.metadata.tables.values()
        for constraint in table.constraints
    }
    with engine.connect() as connection:
        deployed = set(
            connection.scalars(
                text(
                    "SELECT con.conname FROM pg_constraint con "
                    "JOIN pg_namespace n ON n.oid = con.connamespace "
                    "WHERE n.nspname = 'memory' AND con.conrelid <> 0 "
                    "AND con.conrelid::regclass::text <> 'memory.alembic_version'"
                )
            )
        )
    assert deployed == expected


def _only_memory_schema(name: str | None, type_: str, parent_names: object) -> bool:
    if type_ == "schema":
        return name == "memory"
    return name != "alembic_version"


def test_append_only_trigger_function_installed(engine: Engine) -> None:
    with engine.connect() as connection:
        triggers = set(
            connection.scalars(
                text(
                    "SELECT tgname FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid "
                    "JOIN pg_namespace n ON n.oid = c.relnamespace "
                    "WHERE n.nspname = 'memory' AND NOT t.tgisinternal"
                )
            )
        )
    assert triggers == {"pm_atomic_memory_revision_append_only", "pm_provenance_append_only"}
