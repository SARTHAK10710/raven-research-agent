"""Candidate generation (Phase 8.4 step 5; 5.4 Phase 8.4 amendment section 20).

Owner-approved 2026-11-22:

- pm_memory_candidate gains ``categories`` (the 5.4.9 categories proposed for
  the candidate, zero or more) and ``evaluation_metadata`` (the 6.2.4-6.2.5
  dimensions without a column of their own). Both are insert-only: the
  existing me_guard_columns trigger lists the mutable columns, and these are
  not among them.
- pm_source_processing_event gains ``outcome_summary``: per-run counts and
  rejected proposals tallied by reason code, on the transition that ends an
  extraction run. Rejected proposals are never stored as candidates.
- me_outbox accepts a third handoff kind, ``personal_resolution``: validated
  candidates of one source, for memory resolution (plan 8.6).

Revision ID: 0011_candidate_generation
Revises: 0010_relevance_assessment
Create Date: 2026-11-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op
from sqlalchemy.dialects import postgresql

revision: str = "0011_candidate_generation"
down_revision: str | None = "0010_relevance_assessment"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MEMORY_CATEGORIES = (
    "personal_preference",
    "goal",
    "decision",
    "important_event",
    "relationship",
    "knowledge",
    "project",
    "commitment",
)
PREVIOUS_HANDOFF_KINDS = ("document_extraction", "personal_extraction")
HANDOFF_KINDS = (*PREVIOUS_HANDOFF_KINDS, "personal_resolution")

CANDIDATE = "pm_memory_candidate"
EVENT = "pm_source_processing_event"
OUTBOX = "me_outbox"

CANDIDATE_CATEGORIES = "categories <@ ARRAY[{}]::varchar[]".format(
    ", ".join(f"'{category}'" for category in MEMORY_CATEGORIES)
)
EVALUATION_METADATA_OBJECT = "jsonb_typeof(evaluation_metadata) = 'object'"
OUTCOME_SUMMARY = (
    "outcome_summary IS NULL OR "
    "(jsonb_typeof(outcome_summary) = 'object' AND event_type = 'transition')"
)


def memory_schema() -> str:
    schema = context.config.attributes["memory_schema"]
    if not isinstance(schema, str):
        raise TypeError("memory_schema must be set by migrations/env.py")
    return schema


def _in(column: str, values: Sequence[str]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


def _outbox_kinds(schema: str, values: Sequence[str]) -> None:
    name = op.f(f"ck_{OUTBOX}_kind")
    op.drop_constraint(name, OUTBOX, schema=schema, type_="check")
    op.create_check_constraint(name, OUTBOX, _in("kind", values), schema=schema)


def upgrade() -> None:
    schema = memory_schema()
    op.add_column(
        CANDIDATE,
        sa.Column(
            "categories", postgresql.ARRAY(sa.String(32)), nullable=False, server_default="{}"
        ),
        schema=schema,
    )
    op.add_column(
        CANDIDATE,
        sa.Column("evaluation_metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        schema=schema,
    )
    op.create_check_constraint(
        op.f(f"ck_{CANDIDATE}_categories"), CANDIDATE, CANDIDATE_CATEGORIES, schema=schema
    )
    op.create_check_constraint(
        op.f(f"ck_{CANDIDATE}_evaluation_metadata_object"),
        CANDIDATE,
        EVALUATION_METADATA_OBJECT,
        schema=schema,
    )
    op.add_column(EVENT, sa.Column("outcome_summary", postgresql.JSONB()), schema=schema)
    op.create_check_constraint(
        op.f(f"ck_{EVENT}_outcome_summary"), EVENT, OUTCOME_SUMMARY, schema=schema
    )
    _outbox_kinds(schema, HANDOFF_KINDS)


def downgrade() -> None:
    # Destructive: drops every candidate's categories and evaluation metadata and
    # every run summary; fails while a resolution handoff is still in the outbox.
    schema = memory_schema()
    _outbox_kinds(schema, PREVIOUS_HANDOFF_KINDS)
    op.drop_constraint(op.f(f"ck_{EVENT}_outcome_summary"), EVENT, schema=schema, type_="check")
    op.drop_column(EVENT, "outcome_summary", schema=schema)
    for name in ("evaluation_metadata_object", "categories"):
        op.drop_constraint(op.f(f"ck_{CANDIDATE}_{name}"), CANDIDATE, schema=schema, type_="check")
    op.drop_column(CANDIDATE, "evaluation_metadata", schema=schema)
    op.drop_column(CANDIDATE, "categories", schema=schema)
