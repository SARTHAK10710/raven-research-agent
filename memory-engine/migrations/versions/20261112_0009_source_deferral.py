"""Deferred Memory Sources and reason codes (Phase 8.4 step 1; 5.4 Phase 8.4 amendment).

Owner-approved 2026-11-12:
- a new source processing state, ``deferred``: held for controlled later
  processing (6.2.2 DEFER; G6 English first);
- ``reason_code`` on pm_source_processing_event, required exactly for
  transitions into ``deferred`` or ``rejected``. ``error_code`` stays for
  failures only.

The event table stays append-only (its 0005 guard has no mutable columns).
Existing rejected events, if any, would violate the new rule; no deployment
holds any yet (the migration fails loudly rather than guessing a reason).

Revision ID: 0009_source_deferral
Revises: 0008_outbox
Create Date: 2026-11-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op

revision: str = "0009_source_deferral"
down_revision: str | None = "0008_outbox"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PREVIOUS_SOURCE_PROCESSING_STATUSES = (
    "validated",
    "queued",
    "processing",
    "extracted",
    "partially_extracted",
    "rejected",
    "parsing_failed",
    "processing_failed",
)
SOURCE_PROCESSING_STATUSES = (*PREVIOUS_SOURCE_PROCESSING_STATUSES, "deferred")
REASON_REQUIRED = "(to_status IN ('deferred', 'rejected')) = (reason_code IS NOT NULL)"
SAFE_REASON = "reason_code IS NULL OR reason_code ~ '^[A-Z][A-Z0-9_]{0,63}$'"

SOURCE = "pm_memory_source"
EVENT = "pm_source_processing_event"
STATUS_CHECKS = ((SOURCE, "processing_status"), (EVENT, "from_status"), (EVENT, "to_status"))


def memory_schema() -> str:
    schema = context.config.attributes["memory_schema"]
    if not isinstance(schema, str):
        raise TypeError("memory_schema must be set by migrations/env.py")
    return schema


def _in(column: str, values: Sequence[str]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


def _replace_status_checks(schema: str, values: Sequence[str]) -> None:
    for table, column in STATUS_CHECKS:
        name = op.f(f"ck_{table}_{column}")
        op.drop_constraint(name, table, schema=schema, type_="check")
        op.create_check_constraint(name, table, _in(column, values), schema=schema)


def upgrade() -> None:
    schema = memory_schema()
    _replace_status_checks(schema, SOURCE_PROCESSING_STATUSES)
    op.add_column(EVENT, sa.Column("reason_code", sa.String(64)), schema=schema)
    op.create_check_constraint(op.f(f"ck_{EVENT}_reason_code"), EVENT, SAFE_REASON, schema=schema)
    op.create_check_constraint(
        op.f(f"ck_{EVENT}_reason_required"), EVENT, REASON_REQUIRED, schema=schema
    )


def downgrade() -> None:
    # Destructive: fails if any source or event uses 'deferred'; drops reason codes.
    schema = memory_schema()
    op.drop_constraint(op.f(f"ck_{EVENT}_reason_required"), EVENT, schema=schema, type_="check")
    op.drop_constraint(op.f(f"ck_{EVENT}_reason_code"), EVENT, schema=schema, type_="check")
    op.drop_column(EVENT, "reason_code", schema=schema)
    _replace_status_checks(schema, PREVIOUS_SOURCE_PROCESSING_STATUSES)
