"""Ingestion fields on the Memory Source (Phase 8.3 step 2).

Adds to pm_memory_source: instruction type and priority (6.2.1 steps 8-9), an
idempotency key unique per owner with the request fingerprint that makes key
reuse with different content detectable (plan 8.3 section 8), the external
source identifier and timestamp, and the normalized-content reference
(6.2.1 AC-05). Owner-approved: no separate ingestion-operation table; status
and history reuse processing_status and pm_source_processing_event.

The 0005 column guard on pm_memory_source is unchanged, so these columns are
immutable once written.

Revision ID: 0007_source_ingestion
Revises: 0006_episode_version
Create Date: 2026-11-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op

revision: str = "0007_source_ingestion"
down_revision: str | None = "0006_episode_version"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INSTRUCTION_TYPES = ("normal", "remember", "forget")
INGESTION_PRIORITIES = ("normal", "high")
IDEMPOTENCY_PAIR = "(idempotency_key IS NULL) = (request_sha256 IS NULL)"
INSTRUCTION_PRIORITY = "instruction_type = 'normal' OR priority = 'high'"

TABLE = "pm_memory_source"
CHECKS: dict[str, str] = {
    "instruction_type": f"instruction_type IN ({', '.join(repr(v) for v in INSTRUCTION_TYPES)})",
    "priority": f"priority IN ({', '.join(repr(v) for v in INGESTION_PRIORITIES)})",
    "idempotency_pair": IDEMPOTENCY_PAIR,
    "request_sha256": "request_sha256 ~ '^[0-9a-f]{64}$'",
    "idempotency_key": "idempotency_key IS NULL OR length(btrim(idempotency_key)) > 0",
    "source_ref": "source_ref IS NULL OR length(btrim(source_ref)) > 0",
    "instruction_priority": INSTRUCTION_PRIORITY,
}


def memory_schema() -> str:
    schema = context.config.attributes["memory_schema"]
    if not isinstance(schema, str):
        raise TypeError("memory_schema must be set by migrations/env.py")
    return schema


def upgrade() -> None:
    schema = memory_schema()
    columns = [
        sa.Column("instruction_type", sa.String(16), server_default="normal", nullable=False),
        sa.Column("priority", sa.String(16), server_default="normal", nullable=False),
        sa.Column("idempotency_key", sa.String(200)),
        sa.Column("request_sha256", sa.String(64)),
        sa.Column("source_ref", sa.String(500)),
        sa.Column("source_timestamp", sa.DateTime(timezone=True)),
        sa.Column("normalized_ref", sa.Text()),
    ]
    for column in columns:
        op.add_column(TABLE, column, schema=schema)
    for name, condition in CHECKS.items():
        op.create_check_constraint(op.f(f"ck_{TABLE}_{name}"), TABLE, condition, schema=schema)
    op.create_index(
        op.f("uq_pm_memory_source_idempotency"),
        TABLE,
        ["owner_id", "idempotency_key"],
        unique=True,
        schema=schema,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )


def downgrade() -> None:
    # Destructive: drops the ingestion fields of every Memory Source in this schema.
    schema = memory_schema()
    op.drop_index(op.f("uq_pm_memory_source_idempotency"), TABLE, schema=schema)
    for name in CHECKS:
        op.drop_constraint(op.f(f"ck_{TABLE}_{name}"), TABLE, schema=schema, type_="check")
    for column in (
        "normalized_ref",
        "source_timestamp",
        "source_ref",
        "request_sha256",
        "idempotency_key",
        "priority",
        "instruction_type",
    ):
        op.drop_column(TABLE, column, schema=schema)
