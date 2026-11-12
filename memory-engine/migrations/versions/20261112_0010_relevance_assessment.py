"""Relevance gate decisions (Phase 8.4 step 2; 5.4 Phase 8.4 amendment section 17).

Owner-approved 2026-11-12: pm_relevance_assessment holds one decision per
extraction run of a Memory Source (6.2.2 step 8): outcome, reason code,
method and version, and per-sentence results as JSON (positions, outcomes,
codes, scores; never the text). It is written in the same transaction as the
source's outcome, is append-only, and becomes a deletion target kind so plan
8.10 removes it with its source.

Revision ID: 0010_relevance_assessment
Revises: 0009_source_deferral
Create Date: 2026-11-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op
from sqlalchemy.dialects import postgresql

revision: str = "0010_relevance_assessment"
down_revision: str | None = "0009_source_deferral"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

RELEVANCE_OUTCOMES = ("process", "defer", "reject")
RELEVANCE_REASON = "(outcome = 'process') = (reason_code IS NULL)"
SAFE_REASON = "reason_code IS NULL OR reason_code ~ '^[A-Z][A-Z0-9_]{0,63}$'"
PREVIOUS_DELETION_TARGET_KINDS = (
    "memory_source",
    "source_processing_event",
    "memory_candidate",
    "candidate_evaluation",
    "atomic_memory",
    "atomic_memory_revision",
    "provenance",
    "document_evidence_ref",
    "entity",
    "entity_alias",
    "entity_mention",
    "entity_resolution",
    "entity_relationship",
    "memory_relationship",
    "memory_entity",
    "episode",
    "episode_membership",
    "episode_event",
    "profile",
    "profile_revision",
    "profile_memory",
    "profile_refresh",
    "memory_category",
    "memory_embedding",
    "correction_request",
    "correction_memory",
)
DELETION_TARGET_KINDS = (*PREVIOUS_DELETION_TARGET_KINDS, "relevance_assessment")

TABLE = "pm_relevance_assessment"
TARGET = "pm_deletion_target"
# No mutable columns: append-only (me_guard_columns, created in 0002).
GUARDED_TABLES: dict[str, tuple[str, ...]] = {TABLE: ()}


def memory_schema() -> str:
    schema = context.config.attributes["memory_schema"]
    if not isinstance(schema, str):
        raise TypeError("memory_schema must be set by migrations/env.py")
    return schema


def _in(column: str, values: Sequence[str]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


def _ck(name: str, condition: str) -> sa.CheckConstraint:
    return sa.CheckConstraint(condition, name=op.f(f"ck_{TABLE}_{name}"))


def _target_kinds(schema: str, values: Sequence[str]) -> None:
    name = op.f(f"ck_{TARGET}_target_kind")
    op.drop_constraint(name, TARGET, schema=schema, type_="check")
    op.create_check_constraint(name, TARGET, _in("target_kind", values), schema=schema)


def upgrade() -> None:
    schema = memory_schema()
    op.create_table(
        TABLE,
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("seq", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("outcome", sa.String(16), nullable=False),
        sa.Column("reason_code", sa.String(64)),
        sa.Column("method", sa.Text(), nullable=False),
        sa.Column("method_version", sa.Text(), nullable=False),
        sa.Column("units", postgresql.JSONB(), nullable=False),
        sa.Column("assessed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{TABLE}")),
        sa.ForeignKeyConstraint(
            ["source_id", "owner_id"],
            [f"{schema}.pm_memory_source.id", f"{schema}.pm_memory_source.owner_id"],
            name=op.f(f"fk_{TABLE}_source_id_pm_memory_source"),
            ondelete="RESTRICT",
        ),
        _ck("outcome", _in("outcome", RELEVANCE_OUTCOMES)),
        _ck("reason_required", RELEVANCE_REASON),
        _ck("reason_code", SAFE_REASON),
        _ck("method", "length(btrim(method)) > 0"),
        _ck("units_array", "jsonb_typeof(units) = 'array'"),
        schema=schema,
    )
    op.create_index(
        op.f(f"ix_{TABLE}_owner_id_source_id"), TABLE, ["owner_id", "source_id"], schema=schema
    )
    for table, mutable in GUARDED_TABLES.items():
        arguments = ", ".join(f"'{column}'" for column in mutable)
        op.execute(
            f'CREATE TRIGGER {table}_guard BEFORE UPDATE ON "{schema}".{table} '
            f'FOR EACH ROW EXECUTE FUNCTION "{schema}".me_guard_columns({arguments})'
        )
    _target_kinds(schema, DELETION_TARGET_KINDS)


def downgrade() -> None:
    # Destructive: drops every relevance decision; fails if the deletion ledger
    # already names a relevance assessment.
    schema = memory_schema()
    _target_kinds(schema, PREVIOUS_DELETION_TARGET_KINDS)
    for table in GUARDED_TABLES:
        op.execute(f'DROP TRIGGER IF EXISTS {table}_guard ON "{schema}".{table}')
    op.drop_index(op.f(f"ix_{TABLE}_owner_id_source_id"), TABLE, schema=schema)
    op.drop_table(TABLE, schema=schema)
