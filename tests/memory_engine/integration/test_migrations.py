"""Plan 8.2 database tests: migration execution, reversibility and model agreement."""

from collections.abc import Callable

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import Connection, Engine, inspect, text

from memory_engine.infrastructure.persistence.base import Base
from memory_engine.infrastructure.persistence.documents import models as _document_models
from memory_engine.infrastructure.persistence.personal import entity_models as _entity_models
from memory_engine.infrastructure.persistence.personal import models

del _document_models, _entity_models  # imported to register their tables on Base.metadata

pytestmark = pytest.mark.integration

CHECK_SCHEMA = "memory_migration_check"
PM_TABLES = {
    "pm_memory_source",
    "pm_memory_candidate",
    "pm_atomic_memory",
    "pm_atomic_memory_revision",
    "pm_provenance",
    "pm_document_evidence_ref",
    "pm_entity",
    "pm_entity_alias",
    "pm_entity_mention",
    "pm_entity_resolution",
    "pm_entity_relationship",
    "pm_memory_relationship",
    "pm_memory_entity",
    "doc_document",
    "doc_document_version",
    "doc_extracted_representation",
    "doc_chunk",
    "doc_chunk_location",
    "doc_embedding",
    "doc_processing_operation",
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


def test_downgrade_to_step_one_keeps_personal_memory_intact(
    engine: Engine,
    make_alembic_config: Callable[[Connection, str], Config],
    drop_schema: Callable[[Connection, str], None],
) -> None:
    try:
        with engine.begin() as connection:
            drop_schema(connection, CHECK_SCHEMA)
            command.upgrade(make_alembic_config(connection, CHECK_SCHEMA), "head")
            command.downgrade(
                make_alembic_config(connection, CHECK_SCHEMA), "0001_personal_memory_core"
            )
        remaining = _tables(engine, CHECK_SCHEMA)
        assert not any(
            name.startswith(("doc_", "pm_entity", "pm_memory_rel")) for name in remaining
        )
        assert "pm_memory_entity" not in remaining
        assert "pm_document_evidence_ref" not in remaining
        assert "pm_provenance" in remaining
        provenance_columns = {
            column["name"] for column in inspect(engine).get_columns("pm_provenance", CHECK_SCHEMA)
        }
        assert "document_evidence_id" not in provenance_columns
    finally:
        with engine.begin() as connection:
            drop_schema(connection, CHECK_SCHEMA)


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
    assert triggers == {
        "pm_atomic_memory_revision_append_only",
        "pm_provenance_append_only",
        "doc_document_guard",
        "doc_document_version_guard",
        "doc_extracted_representation_guard",
        "doc_chunk_guard",
        "doc_chunk_location_guard",
        "doc_embedding_guard",
        "doc_processing_operation_guard",
        "pm_document_evidence_ref_guard",
        "pm_entity_guard",
        "pm_entity_alias_guard",
        "pm_entity_mention_guard",
        "pm_entity_resolution_guard",
        "pm_entity_relationship_guard",
        "pm_memory_relationship_guard",
        "pm_memory_entity_guard",
    }
