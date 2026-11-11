"""Alembic environment for the Memory Engine schema.

Connection: an already-open connection passed in ``config.attributes["connection"]``
(used by tests), or otherwise one built from the validated Memory Engine settings.

Schema: ``config.attributes["memory_schema"]`` if given, else the configured
``RAVEN_MEMORY__DATABASE__SCHEMA_NAME`` (default ``memory``). Migrations read it
back through ``memory_schema()`` in each revision. The Alembic version table
lives in the same schema, so each schema is migrated independently.
"""

import re
from logging.config import fileConfig

from alembic import context
from sqlalchemy import Connection, create_engine, pool, text

from memory_engine.config import load_settings
from memory_engine.infrastructure.persistence.base import Base
from memory_engine.infrastructure.persistence.database import build_database_url
from memory_engine.infrastructure.persistence.documents import models as _document_models
from memory_engine.infrastructure.persistence.personal import models as _personal_models

# Imported for their side effect: register the pm_ and doc_ tables on Base.metadata.
del _document_models, _personal_models

SCHEMA_PATTERN = re.compile(r"^[a-z_][a-z0-9_]*$")

config = context.config
if config.config_file_name is not None and not config.attributes.get("connection"):
    fileConfig(config.config_file_name, disable_existing_loggers=False)


def _resolve_schema() -> str:
    schema = config.attributes.get("memory_schema")
    if schema is None:
        schema = load_settings().database.schema_name
    if not isinstance(schema, str) or not SCHEMA_PATTERN.fullmatch(schema):
        raise ValueError("memory schema name must match ^[a-z_][a-z0-9_]*$")
    config.attributes["memory_schema"] = schema
    return schema


def _run(connection: Connection, schema: str) -> None:
    # Identifier is validated above; schema names cannot be bound parameters.
    connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
    context.configure(
        connection=connection,
        target_metadata=Base.metadata,
        version_table_schema=schema,
        include_schemas=False,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    schema = _resolve_schema()
    supplied = config.attributes.get("connection")
    if isinstance(supplied, Connection):
        _run(supplied, schema)
        return
    settings = load_settings().database
    engine = create_engine(
        build_database_url(settings), poolclass=pool.NullPool, hide_parameters=True
    )
    with engine.begin() as connection:
        _run(connection, schema)
    engine.dispose()


if context.is_offline_mode():
    raise RuntimeError("Offline (SQL script) migrations are not supported for the Memory Engine")
run_migrations_online()
