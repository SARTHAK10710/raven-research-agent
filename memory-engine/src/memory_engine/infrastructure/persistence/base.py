"""Declarative base for all Memory Engine tables.

Tables are declared in the logical ``memory`` schema (Phase 7.2). A deployment
that configures a different schema name maps it at execution time through
SQLAlchemy's ``schema_translate_map`` (see ``database.create_database_engine``),
so model definitions never depend on configuration.

Table prefixes: ``pm_`` Personal Memory, ``doc_`` Document Intelligence,
``me_`` shared engine plumbing (Phase 7.1 section 23.3).
"""

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

MEMORY_SCHEMA = "memory"

# Deterministic constraint names, so migrations and error handling can rely on them.
NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    # First column only: two-column names would exceed PostgreSQL's 63-character limit.
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(schema=MEMORY_SCHEMA, naming_convention=NAMING_CONVENTION)
