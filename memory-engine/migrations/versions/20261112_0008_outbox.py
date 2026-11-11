"""Transactional outbox, me_outbox (Phase 8.3 step 4; 7.1 sections 23.6 and 24.3).

One row per handoff (a Memory Source to extraction, a document processing
operation to the document pipeline), written in the same transaction as the
record it hands off. A relay publishes pending rows to RabbitMQ and marks them
published; failures count attempts and back off; after the configured maximum a
row becomes ``failed`` until an explicit retry.

The envelope is the 7.4 section 7 task envelope (schema_version 1): identifiers
and object keys only, never content. No foreign key to the subject: it lives in
either domain, and only the evidence path may cross them; plan 8.10 deletion
removes outbox rows explicitly.

Only the publication state is mutable (me_guard_columns, created in 0002).

Revision ID: 0008_outbox
Revises: 0007_source_ingestion
Create Date: 2026-11-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op
from sqlalchemy.dialects import postgresql

revision: str = "0008_outbox"
down_revision: str | None = "0007_source_ingestion"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

HANDOFF_KINDS = ("document_extraction", "personal_extraction")
OUTBOX_STATUSES = ("pending", "published", "failed")
PUBLISHED_AT_RULE = "(status = 'published') = (published_at IS NOT NULL)"
SAFE_LAST_ERROR = "last_error_code IS NULL OR last_error_code ~ '^[A-Z][A-Z0-9_]{0,63}$'"

TABLE = "me_outbox"
GUARDED_TABLES: dict[str, tuple[str, ...]] = {
    TABLE: (
        "status",
        "attempts",
        "next_attempt_at",
        "last_error_code",
        "published_at",
        "updated_at",
    ),
}


def memory_schema() -> str:
    schema = context.config.attributes["memory_schema"]
    if not isinstance(schema, str):
        raise TypeError("memory_schema must be set by migrations/env.py")
    return schema


def _in(column: str, values: Sequence[str]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


def _ck(name: str, condition: str) -> sa.CheckConstraint:
    return sa.CheckConstraint(condition, name=op.f(f"ck_{TABLE}_{name}"))


def upgrade() -> None:
    schema = memory_schema()
    op.create_table(
        TABLE,
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("subject_id", sa.Uuid(), nullable=False),
        sa.Column("envelope", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_error_code", sa.String(64)),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{TABLE}")),
        sa.UniqueConstraint(
            "owner_id", "kind", "subject_id", name=op.f(f"uq_{TABLE}_owner_id_kind_subject_id")
        ),
        _ck("kind", _in("kind", HANDOFF_KINDS)),
        _ck("status", _in("status", OUTBOX_STATUSES)),
        _ck("attempts", "attempts >= 0"),
        _ck("published_at", PUBLISHED_AT_RULE),
        _ck("last_error_code", SAFE_LAST_ERROR),
        schema=schema,
    )
    op.create_index(
        op.f("ix_me_outbox_due"),
        TABLE,
        ["next_attempt_at"],
        schema=schema,
        postgresql_where=sa.text("status = 'pending'"),
    )
    for table, mutable in GUARDED_TABLES.items():
        arguments = ", ".join(f"'{column}'" for column in mutable)
        op.execute(
            f'CREATE TRIGGER {table}_guard BEFORE UPDATE ON "{schema}".{table} '
            f'FOR EACH ROW EXECUTE FUNCTION "{schema}".me_guard_columns({arguments})'
        )


def downgrade() -> None:
    # Destructive: drops every pending handoff. Records stay validated/created and
    # are not re-handed-off by anything until the table returns.
    schema = memory_schema()
    for table in GUARDED_TABLES:
        op.execute(f'DROP TRIGGER IF EXISTS {table}_guard ON "{schema}".{table}')
    op.drop_index(op.f("ix_me_outbox_due"), TABLE, schema=schema)
    op.drop_table(TABLE, schema=schema)
