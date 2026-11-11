"""Processing, evaluation, correction and deletion records (Phase 8.2 step 5).

Creates pm_source_processing_event, pm_candidate_evaluation,
pm_correction_request, pm_correction_memory, pm_deletion_operation and
pm_deletion_target (Decisions 5.4.24-5.4.26, 5.4.28; 6.5.8-6.5.9).

* Processing events and evaluations are append-only history; the source and
  candidate keep their current state, which now changes only in its state
  columns (me_guard_columns on pm_memory_source and pm_memory_candidate).
* The deletion ledger names records by kind and identifier, without foreign
  keys, so it outlives purged records and can be replayed after a restore.

Vocabularies and rule texts are FROZEN here; unit tests compare them with the
domain enums and the models.

Revision ID: 0005_processing_deletion
Revises: 0004_episodes_profiles
Create Date: 2026-11-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op
from sqlalchemy.dialects import postgresql

revision: str = "0005_processing_deletion"
down_revision: str | None = "0004_episodes_profiles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SOURCE_PROCESSING_STATUSES = (
    "validated",
    "queued",
    "processing",
    "extracted",
    "partially_extracted",
    "rejected",
    "parsing_failed",
    "processing_failed",
)
CANDIDATE_STATUSES = ("candidate", "validated", "needs_review", "rejected", "superseded")
PROCESSING_EVENT_TYPES = ("transition", "failure", "retry", "recovery")
EVALUATION_OUTCOMES = ("proceed", "needs_review", "reject", "defer")
CORRECTION_STATUSES = ("open", "accepted", "rejected", "withdrawn", "deleted")
DELETION_REQUEST_KINDS = ("user_request", "account", "administrative", "system")
DELETION_OPERATION_STATUSES = (
    "requested",
    "validating",
    "approved",
    "in_progress",
    "propagating",
    "verifying",
    "completed",
    "partially_completed",
    "failed",
    "requires_reconciliation",
)
DELETION_TARGET_KINDS = (
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
DELETION_ACTIONS = ("delete", "invalidate", "refresh")
DELETION_TARGET_STATES = ("pending", "propagated", "verified", "failed")

OUTCOME_STATUSES = (
    "(outcome = 'proceed' AND to_status IN ('candidate', 'validated'))"
    " OR (outcome = 'needs_review' AND to_status IN ('needs_review'))"
    " OR (outcome = 'reject' AND to_status IN ('rejected'))"
    " OR (outcome = 'defer' AND to_status IN ('candidate'))"
)
RESOLVED_CORRECTION = "'accepted', 'rejected', 'withdrawn'"
FINISHED_DELETION = "'completed', 'partially_completed', 'failed'"

GUARDED_TABLES: dict[str, tuple[str, ...]] = {
    "pm_memory_source": ("processing_status", "content_ref", "content_sha256", "updated_at"),
    "pm_memory_candidate": ("status", "importance", "confidence", "updated_at"),
    "pm_source_processing_event": (),
    "pm_candidate_evaluation": (),
    "pm_correction_request": (
        "status",
        "proposed_change",
        "evidence",
        "resolution_note",
        "resolved_at",
        "updated_at",
    ),
    "pm_correction_memory": ("applied_revision_number", "updated_at"),
    "pm_deletion_operation": ("status", "finished_at", "error_code", "updated_at"),
    "pm_deletion_target": ("state", "attempts", "error_code", "updated_at"),
}


def memory_schema() -> str:
    schema = context.config.attributes["memory_schema"]
    if not isinstance(schema, str):
        raise TypeError("memory_schema must be set by migrations/env.py")
    return schema


def _in(column: str, values: Sequence[str]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


def _safe_code(column: str) -> str:
    return f"{column} IS NULL OR {column} ~ '^[A-Z][A-Z0-9_]{{0,63}}$'"


def _ck(table: str, name: str, condition: str) -> sa.CheckConstraint:
    return sa.CheckConstraint(condition, name=op.f(f"ck_{table}_{name}"))


def _owner_fk(table: str, column: str, target: str, schema: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        [column, "owner_id"],
        [f"{schema}.{target}.id", f"{schema}.{target}.owner_id"],
        name=op.f(f"fk_{table}_{column}_{target}"),
        ondelete="RESTRICT",
    )


def _revision_fk(name: str, column: str, schema: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["memory_id", column],
        [
            f"{schema}.pm_atomic_memory_revision.memory_id",
            f"{schema}.pm_atomic_memory_revision.revision_number",
        ],
        name=op.f(name),
        ondelete="RESTRICT",
    )


def _score(table: str, column: str) -> sa.CheckConstraint:
    return _ck(table, column, f"{column} IS NULL OR ({column} >= 0 AND {column} <= 1)")


def _created() -> sa.Column[object]:
    return sa.Column(
        "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )


def _updated() -> sa.Column[object]:
    return sa.Column(
        "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )


def _ts(name: str, *, nullable: bool = True) -> sa.Column[object]:
    return sa.Column(name, sa.DateTime(timezone=True), nullable=nullable)


def _seq() -> sa.Column[object]:
    return sa.Column("seq", sa.BigInteger(), sa.Identity(always=True), nullable=False)


def _index(table: str, columns: list[str], schema: str) -> None:
    op.create_index(op.f(f"ix_{table}_{'_'.join(columns)}"), table, columns, schema=schema)


def upgrade() -> None:
    schema = memory_schema()

    t = "pm_source_processing_event"
    op.create_table(
        t,
        sa.Column("id", sa.Uuid()),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        _seq(),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(16), nullable=False),
        sa.Column("from_status", sa.String(32), nullable=False),
        sa.Column("to_status", sa.String(32), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(64)),
        _ts("occurred_at", nullable=False),
        _created(),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{t}")),
        _owner_fk(t, "source_id", "pm_memory_source", schema),
        _ck(t, "event_type", _in("event_type", PROCESSING_EVENT_TYPES)),
        _ck(t, "from_status", _in("from_status", SOURCE_PROCESSING_STATUSES)),
        _ck(t, "to_status", _in("to_status", SOURCE_PROCESSING_STATUSES)),
        _ck(t, "status_changes", "from_status <> to_status"),
        _ck(t, "attempt_positive", "attempt >= 1"),
        _ck(t, "failure_code", "(event_type = 'failure') = (error_code IS NOT NULL)"),
        _ck(t, "error_code", _safe_code("error_code")),
        schema=schema,
    )
    _index(t, ["owner_id", "source_id"], schema)

    t = "pm_candidate_evaluation"
    op.create_table(
        t,
        sa.Column("id", sa.Uuid()),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        _seq(),
        sa.Column("candidate_id", sa.Uuid(), nullable=False),
        sa.Column("outcome", sa.String(16), nullable=False),
        sa.Column("from_status", sa.String(32), nullable=False),
        sa.Column("to_status", sa.String(32), nullable=False),
        sa.Column("importance", sa.Double()),
        sa.Column("confidence", sa.Double()),
        sa.Column("reason_code", sa.String(64)),
        sa.Column("method", sa.Text(), nullable=False),
        sa.Column("method_version", sa.Text(), nullable=False),
        _ts("evaluated_at", nullable=False),
        _created(),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{t}")),
        _owner_fk(t, "candidate_id", "pm_memory_candidate", schema),
        _ck(t, "outcome", _in("outcome", EVALUATION_OUTCOMES)),
        _ck(t, "from_status", _in("from_status", CANDIDATE_STATUSES)),
        _ck(t, "to_status", _in("to_status", CANDIDATE_STATUSES)),
        _ck(t, "outcome_status", OUTCOME_STATUSES),
        _score(t, "importance"),
        _score(t, "confidence"),
        _ck(t, "reason_code", _safe_code("reason_code")),
        _ck(t, "method", "length(btrim(method)) > 0"),
        schema=schema,
    )
    _index(t, ["owner_id", "candidate_id"], schema)

    t = "pm_correction_request"
    op.create_table(
        t,
        sa.Column("id", sa.Uuid()),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("proposed_change", postgresql.JSONB()),
        sa.Column("evidence", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("resolution_note", sa.Text()),
        _ts("requested_at", nullable=False),
        _ts("resolved_at"),
        _created(),
        _updated(),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{t}")),
        sa.UniqueConstraint("id", "owner_id", name=op.f(f"uq_{t}_id_owner_id")),
        _ck(t, "status", _in("status", CORRECTION_STATUSES)),
        _ck(t, "content_until_deleted", "(status = 'deleted') = (proposed_change IS NULL)"),
        _ck(
            t,
            "deleted_keeps_no_content",
            "status <> 'deleted' OR (evidence = '{}'::jsonb AND resolution_note IS NULL)",
        ),
        _ck(
            t,
            "open_unresolved",
            "status <> 'open' OR (resolved_at IS NULL AND resolution_note IS NULL)",
        ),
        _ck(
            t,
            "resolved_has_time",
            f"status NOT IN ({RESOLVED_CORRECTION}) OR resolved_at IS NOT NULL",
        ),
        _ck(
            t,
            "resolved_after_requested",
            "resolved_at IS NULL OR resolved_at >= requested_at",
        ),
        _ck(
            t,
            "resolution_note",
            "resolution_note IS NULL OR length(btrim(resolution_note)) > 0",
        ),
        schema=schema,
    )
    _index(t, ["owner_id", "status"], schema)

    t = "pm_correction_memory"
    op.create_table(
        t,
        sa.Column("id", sa.Uuid()),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("memory_id", sa.Uuid(), nullable=False),
        sa.Column("base_revision_number", sa.Integer(), nullable=False),
        sa.Column("applied_revision_number", sa.Integer()),
        _created(),
        _updated(),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{t}")),
        sa.UniqueConstraint("request_id", "memory_id", name=op.f(f"uq_{t}_request_id_memory_id")),
        _owner_fk(t, "request_id", "pm_correction_request", schema),
        _owner_fk(t, "memory_id", "pm_atomic_memory", schema),
        _revision_fk("fk_pm_correction_memory_base_revision", "base_revision_number", schema),
        _revision_fk("fk_pm_correction_memory_applied_revision", "applied_revision_number", schema),
        _ck(t, "base_revision_positive", "base_revision_number >= 1"),
        _ck(
            t,
            "applied_after_base",
            "applied_revision_number IS NULL OR applied_revision_number > base_revision_number",
        ),
        schema=schema,
    )
    _index(t, ["owner_id", "memory_id"], schema)

    t = "pm_deletion_operation"
    op.create_table(
        t,
        sa.Column("id", sa.Uuid()),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("request_kind", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("idempotency_key", sa.String(200), nullable=False),
        _ts("requested_at", nullable=False),
        _ts("finished_at"),
        sa.Column("error_code", sa.String(64)),
        _created(),
        _updated(),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{t}")),
        sa.UniqueConstraint("id", "owner_id", name=op.f(f"uq_{t}_id_owner_id")),
        sa.UniqueConstraint(
            "owner_id", "idempotency_key", name=op.f(f"uq_{t}_owner_id_idempotency_key")
        ),
        _ck(t, "request_kind", _in("request_kind", DELETION_REQUEST_KINDS)),
        _ck(t, "status", _in("status", DELETION_OPERATION_STATUSES)),
        _ck(
            t,
            "finished_has_time",
            f"(status IN ({FINISHED_DELETION})) = (finished_at IS NOT NULL)",
        ),
        _ck(
            t,
            "finished_after_requested",
            "finished_at IS NULL OR finished_at >= requested_at",
        ),
        _ck(t, "failure_code", "status <> 'failed' OR error_code IS NOT NULL"),
        _ck(t, "completed_clean", "status <> 'completed' OR error_code IS NULL"),
        _ck(t, "error_code", _safe_code("error_code")),
        _ck(t, "idempotency_key", "length(btrim(idempotency_key)) > 0"),
        schema=schema,
    )
    _index(t, ["owner_id", "status"], schema)

    t = "pm_deletion_target"
    op.create_table(
        t,
        sa.Column("id", sa.Uuid()),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("operation_id", sa.Uuid(), nullable=False),
        sa.Column("target_kind", sa.String(32), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("direct", sa.Boolean(), nullable=False),
        sa.Column("action", sa.String(16), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(64)),
        _created(),
        _updated(),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{t}")),
        sa.UniqueConstraint(
            "operation_id",
            "target_kind",
            "target_id",
            name=op.f(f"uq_{t}_operation_id_target_kind_target_id"),
        ),
        _owner_fk(t, "operation_id", "pm_deletion_operation", schema),
        _ck(t, "target_kind", _in("target_kind", DELETION_TARGET_KINDS)),
        _ck(t, "action", _in("action", DELETION_ACTIONS)),
        _ck(t, "state", _in("state", DELETION_TARGET_STATES)),
        _ck(t, "attempts", "attempts >= 0"),
        _ck(t, "failure_code", "(state = 'failed') = (error_code IS NOT NULL)"),
        _ck(t, "error_code", _safe_code("error_code")),
        schema=schema,
    )
    _index(t, ["owner_id", "target_kind", "target_id"], schema)

    for table, mutable in GUARDED_TABLES.items():
        arguments = ", ".join(f"'{column}'" for column in mutable)
        op.execute(
            f'CREATE TRIGGER {table}_guard BEFORE UPDATE ON "{schema}".{table} '
            f'FOR EACH ROW EXECUTE FUNCTION "{schema}".me_guard_columns({arguments})'
        )


def downgrade() -> None:
    # Destructive: drops processing, evaluation, correction and deletion history in
    # this schema, including the deletion ledger that restores rely on. Never run
    # against real data without a backup.
    schema = memory_schema()
    for table in GUARDED_TABLES:
        op.execute(f'DROP TRIGGER IF EXISTS {table}_guard ON "{schema}".{table}')
    for table in (
        "pm_deletion_target",
        "pm_deletion_operation",
        "pm_correction_memory",
        "pm_correction_request",
        "pm_candidate_evaluation",
        "pm_source_processing_event",
    ):
        op.drop_table(table, schema=schema)
