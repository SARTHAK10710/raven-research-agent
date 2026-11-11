"""Personal Memory core tables (Phase 8.2 step 1).

Creates pm_memory_source, pm_memory_candidate, pm_atomic_memory,
pm_atomic_memory_revision and pm_provenance with owner-scoped composite foreign
keys, vocabulary check constraints and append-only triggers.

Vocabularies are FROZEN here as literals, never imported from the live enums:
a migration must keep producing the same schema after the code moves on. A unit
test checks that they still equal memory_engine.domain.vocabulary.

Revision ID: 0001_personal_memory_core
Revises:
Create Date: 2026-11-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op
from sqlalchemy.dialects import postgresql

revision: str = "0001_personal_memory_core"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SOURCE_TYPES = ("text", "conversation", "document")
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
CANDIDATE_ORIGINS = ("explicit", "inferred", "unresolved")
MEMORY_ORIGINS = ("explicit", "inferred")
MEMORY_LIFECYCLE_STATUSES = (
    "active",
    "historical",
    "needs_review",
    "retracted",
    "deletion_pending",
    "deleted",
)
REVISION_CHANGE_TYPES = (
    "created",
    "updated",
    "corrected",
    "evidence_added",
    "superseded",
    "expired",
    "retracted",
    "reclassified",
)
PROVENANCE_ROLES = ("origin", "supporting", "contradicting", "correcting")
PROVENANCE_ORIGIN_KINDS = ("explicit", "inferred", "system_generated")

CONTENT_MATCHES_LIFECYCLE = (
    "(lifecycle_status = 'deleted' AND content IS NULL)"
    " OR (lifecycle_status <> 'deleted' AND content IS NOT NULL AND length(btrim(content)) > 0)"
)
APPEND_ONLY_TABLES = ("pm_atomic_memory_revision", "pm_provenance")


def memory_schema() -> str:
    schema = context.config.attributes["memory_schema"]
    if not isinstance(schema, str):
        raise TypeError("memory_schema must be set by migrations/env.py")
    return schema


def _in(column: str, values: Sequence[str]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


def _score(table: str, column: str) -> sa.CheckConstraint:
    return sa.CheckConstraint(
        f"{column} IS NULL OR ({column} >= 0 AND {column} <= 1)", name=op.f(f"ck_{table}_{column}")
    )


def _timestamps(*, updated: bool) -> list[sa.Column[object]]:
    columns: list[sa.Column[object]] = [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        )
    ]
    if updated:
        columns.append(
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            )
        )
    return columns


def _json(name: str) -> sa.Column[object]:
    return sa.Column(name, postgresql.JSONB(), server_default="{}", nullable=False)


def upgrade() -> None:
    schema = memory_schema()

    op.create_table(
        "pm_memory_source",
        sa.Column("id", sa.Uuid()),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("source_type", sa.String(32), nullable=False),
        sa.Column("processing_status", sa.String(32), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("content_ref", sa.Text()),
        sa.Column("content_sha256", sa.String(64)),
        *_timestamps(updated=True),
        sa.PrimaryKeyConstraint("id", name="pk_pm_memory_source"),
        sa.UniqueConstraint("id", "owner_id", name="uq_pm_memory_source_id_owner_id"),
        sa.CheckConstraint(
            _in("source_type", SOURCE_TYPES), name=op.f("ck_pm_memory_source_source_type")
        ),
        sa.CheckConstraint(
            _in("processing_status", SOURCE_PROCESSING_STATUSES),
            name=op.f("ck_pm_memory_source_processing_status"),
        ),
        sa.CheckConstraint(
            "content_sha256 ~ '^[0-9a-f]{64}$'", name=op.f("ck_pm_memory_source_content_sha256")
        ),
        schema=schema,
    )
    op.create_index(
        "ix_pm_memory_source_owner_id_received_at",
        "pm_memory_source",
        ["owner_id", "received_at"],
        schema=schema,
    )

    op.create_table(
        "pm_memory_candidate",
        sa.Column("id", sa.Uuid()),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("proposition", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("origin", sa.String(32), nullable=False),
        sa.Column("importance", sa.Double()),
        sa.Column("confidence", sa.Double()),
        sa.Column("extraction_confidence", sa.Double()),
        _json("context"),
        _json("temporal"),
        _json("extraction_metadata"),
        *_timestamps(updated=True),
        sa.PrimaryKeyConstraint("id", name="pk_pm_memory_candidate"),
        sa.UniqueConstraint("id", "owner_id", name="uq_pm_memory_candidate_id_owner_id"),
        sa.ForeignKeyConstraint(
            ["source_id", "owner_id"],
            [f"{schema}.pm_memory_source.id", f"{schema}.pm_memory_source.owner_id"],
            name="fk_pm_memory_candidate_source_id_pm_memory_source",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            _in("status", CANDIDATE_STATUSES), name=op.f("ck_pm_memory_candidate_status")
        ),
        sa.CheckConstraint(
            _in("origin", CANDIDATE_ORIGINS), name=op.f("ck_pm_memory_candidate_origin")
        ),
        sa.CheckConstraint(
            "length(btrim(proposition)) > 0",
            name=op.f("ck_pm_memory_candidate_proposition_not_blank"),
        ),
        sa.CheckConstraint(
            "NOT (origin = 'unresolved' AND status = 'validated')",
            name=op.f("ck_pm_memory_candidate_unresolved_not_validated"),
        ),
        _score("pm_memory_candidate", "importance"),
        _score("pm_memory_candidate", "confidence"),
        _score("pm_memory_candidate", "extraction_confidence"),
        schema=schema,
    )
    op.create_index(
        "ix_pm_memory_candidate_owner_id_source_id",
        "pm_memory_candidate",
        ["owner_id", "source_id"],
        schema=schema,
    )
    op.create_index(
        "ix_pm_memory_candidate_owner_id_status",
        "pm_memory_candidate",
        ["owner_id", "status"],
        schema=schema,
    )

    op.create_table(
        "pm_atomic_memory",
        sa.Column("id", sa.Uuid()),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("content", sa.Text()),
        _json("structured"),
        _json("context"),
        sa.Column("origin", sa.String(32), nullable=False),
        sa.Column("lifecycle_status", sa.String(32), nullable=False),
        sa.Column("importance", sa.Double()),
        sa.Column("confidence", sa.Double()),
        sa.Column("valid_from", sa.DateTime(timezone=True)),
        sa.Column("valid_to", sa.DateTime(timezone=True)),
        sa.Column("observed_at", sa.DateTime(timezone=True)),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("superseded_at", sa.DateTime(timezone=True)),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        *_timestamps(updated=True),
        sa.PrimaryKeyConstraint("id", name="pk_pm_atomic_memory"),
        sa.UniqueConstraint("id", "owner_id", name="uq_pm_atomic_memory_id_owner_id"),
        sa.CheckConstraint(_in("origin", MEMORY_ORIGINS), name=op.f("ck_pm_atomic_memory_origin")),
        sa.CheckConstraint(
            _in("lifecycle_status", MEMORY_LIFECYCLE_STATUSES),
            name=op.f("ck_pm_atomic_memory_lifecycle_status"),
        ),
        sa.CheckConstraint(
            CONTENT_MATCHES_LIFECYCLE, name=op.f("ck_pm_atomic_memory_content_matches_lifecycle")
        ),
        sa.CheckConstraint(
            "revision_number >= 1", name=op.f("ck_pm_atomic_memory_revision_number_positive")
        ),
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from",
            name=op.f("ck_pm_atomic_memory_valid_interval"),
        ),
        sa.CheckConstraint(
            "superseded_at IS NULL OR superseded_at >= recorded_at",
            name=op.f("ck_pm_atomic_memory_superseded_after_recorded"),
        ),
        _score("pm_atomic_memory", "importance"),
        _score("pm_atomic_memory", "confidence"),
        schema=schema,
    )
    op.create_index(
        "ix_pm_atomic_memory_owner_id_lifecycle_status",
        "pm_atomic_memory",
        ["owner_id", "lifecycle_status"],
        schema=schema,
    )

    op.create_table(
        "pm_atomic_memory_revision",
        sa.Column("id", sa.Uuid()),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("memory_id", sa.Uuid(), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("change_type", sa.String(32), nullable=False),
        sa.Column("content", sa.Text()),
        _json("structured"),
        _json("context"),
        sa.Column("origin", sa.String(32), nullable=False),
        sa.Column("lifecycle_status", sa.String(32), nullable=False),
        sa.Column("importance", sa.Double()),
        sa.Column("confidence", sa.Double()),
        sa.Column("valid_from", sa.DateTime(timezone=True)),
        sa.Column("valid_to", sa.DateTime(timezone=True)),
        sa.Column("observed_at", sa.DateTime(timezone=True)),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.Text()),
        *_timestamps(updated=False),
        sa.PrimaryKeyConstraint("id", name="pk_pm_atomic_memory_revision"),
        sa.UniqueConstraint(
            "memory_id",
            "revision_number",
            name="uq_pm_atomic_memory_revision_memory_id_revision_number",
        ),
        sa.ForeignKeyConstraint(
            ["memory_id", "owner_id"],
            [f"{schema}.pm_atomic_memory.id", f"{schema}.pm_atomic_memory.owner_id"],
            name="fk_pm_atomic_memory_revision_memory_id_pm_atomic_memory",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            _in("change_type", REVISION_CHANGE_TYPES),
            name=op.f("ck_pm_atomic_memory_revision_change_type"),
        ),
        sa.CheckConstraint(
            _in("origin", MEMORY_ORIGINS), name=op.f("ck_pm_atomic_memory_revision_origin")
        ),
        sa.CheckConstraint(
            _in("lifecycle_status", MEMORY_LIFECYCLE_STATUSES),
            name=op.f("ck_pm_atomic_memory_revision_lifecycle_status"),
        ),
        sa.CheckConstraint(
            CONTENT_MATCHES_LIFECYCLE,
            name=op.f("ck_pm_atomic_memory_revision_content_matches_lifecycle"),
        ),
        sa.CheckConstraint(
            "revision_number >= 1",
            name=op.f("ck_pm_atomic_memory_revision_revision_number_positive"),
        ),
        sa.CheckConstraint(
            "(revision_number = 1) = (change_type = 'created')",
            name=op.f("ck_pm_atomic_memory_revision_created_is_first"),
        ),
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from",
            name=op.f("ck_pm_atomic_memory_revision_valid_interval"),
        ),
        _score("pm_atomic_memory_revision", "importance"),
        _score("pm_atomic_memory_revision", "confidence"),
        schema=schema,
    )
    op.create_index(
        "ix_pm_atomic_memory_revision_owner_id_memory_id",
        "pm_atomic_memory_revision",
        ["owner_id", "memory_id"],
        schema=schema,
    )

    op.create_table(
        "pm_provenance",
        sa.Column("id", sa.Uuid()),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("memory_id", sa.Uuid(), nullable=False),
        sa.Column("revision_number", sa.Integer()),
        sa.Column("source_id", sa.Uuid()),
        sa.Column("candidate_id", sa.Uuid()),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("origin_kind", sa.String(32), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        *_timestamps(updated=False),
        sa.PrimaryKeyConstraint("id", name="pk_pm_provenance"),
        sa.ForeignKeyConstraint(
            ["memory_id", "owner_id"],
            [f"{schema}.pm_atomic_memory.id", f"{schema}.pm_atomic_memory.owner_id"],
            name="fk_pm_provenance_memory_id_pm_atomic_memory",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["memory_id", "revision_number"],
            [
                f"{schema}.pm_atomic_memory_revision.memory_id",
                f"{schema}.pm_atomic_memory_revision.revision_number",
            ],
            name="fk_pm_provenance_memory_id_pm_atomic_memory_revision",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_id", "owner_id"],
            [f"{schema}.pm_memory_source.id", f"{schema}.pm_memory_source.owner_id"],
            name="fk_pm_provenance_source_id_pm_memory_source",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["candidate_id", "owner_id"],
            [f"{schema}.pm_memory_candidate.id", f"{schema}.pm_memory_candidate.owner_id"],
            name="fk_pm_provenance_candidate_id_pm_memory_candidate",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(_in("role", PROVENANCE_ROLES), name=op.f("ck_pm_provenance_role")),
        sa.CheckConstraint(
            _in("origin_kind", PROVENANCE_ORIGIN_KINDS), name=op.f("ck_pm_provenance_origin_kind")
        ),
        sa.CheckConstraint(
            "source_id IS NOT NULL OR candidate_id IS NOT NULL",
            name=op.f("ck_pm_provenance_references_evidence"),
        ),
        sa.CheckConstraint(
            "revision_number IS NULL OR revision_number >= 1",
            name=op.f("ck_pm_provenance_revision_number_positive"),
        ),
        schema=schema,
    )
    op.create_index(
        "ix_pm_provenance_owner_id_memory_id",
        "pm_provenance",
        ["owner_id", "memory_id"],
        schema=schema,
    )

    # Append-only records: reject UPDATE at the database level. DELETE stays
    # possible for the explicit deletion workflow (plan 8.10).
    op.execute(
        f"""
        CREATE FUNCTION "{schema}".pm_reject_update() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'append-only table: % rows cannot be updated', TG_TABLE_NAME
                USING ERRCODE = 'integrity_constraint_violation';
        END;
        $$
        """
    )
    for table in APPEND_ONLY_TABLES:
        op.execute(
            f'CREATE TRIGGER {table}_append_only BEFORE UPDATE ON "{schema}".{table} '
            f'FOR EACH ROW EXECUTE FUNCTION "{schema}".pm_reject_update()'
        )


def downgrade() -> None:
    # Destructive: drops all Personal Memory core data in this schema. Never run
    # against a database holding real data without a verified backup.
    schema = memory_schema()
    for table in APPEND_ONLY_TABLES:
        op.execute(f'DROP TRIGGER IF EXISTS {table}_append_only ON "{schema}".{table}')
    op.execute(f'DROP FUNCTION IF EXISTS "{schema}".pm_reject_update()')
    op.drop_table("pm_provenance", schema=schema)
    op.drop_table("pm_atomic_memory_revision", schema=schema)
    op.drop_table("pm_atomic_memory", schema=schema)
    op.drop_table("pm_memory_candidate", schema=schema)
    op.drop_table("pm_memory_source", schema=schema)
