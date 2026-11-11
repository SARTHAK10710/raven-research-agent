"""Entities, mentions, resolution history and relationships (Phase 8.2 step 3).

Creates pm_entity, pm_entity_alias, pm_entity_mention, pm_entity_resolution,
pm_entity_relationship, pm_memory_relationship and pm_memory_entity.

* Entities are private only (Decision 11): scope = 'private' is checked.
* Symmetric relationships are stored once (lower id as source); a partial
  unique index allows one current row per endpoint pair and type.
* me_guard_columns (installed by 0002) limits updates: aliases, resolution
  records and associations are append-only; mentions may change only their
  resolution; relationships may only be closed.

Vocabularies and rule texts are FROZEN here; unit tests compare them with the
domain enums and the models.

Revision ID: 0003_entities_and_relationships
Revises: 0002_document_intelligence
Create Date: 2026-11-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op
from sqlalchemy.dialects import postgresql

revision: str = "0003_entities_and_relationships"
down_revision: str | None = "0002_document_intelligence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ENTITY_SCOPES = ("private", "shared")
ENTITY_TYPES = (
    "person",
    "organization",
    "project",
    "product",
    "place",
    "institution",
    "technology",
    "event",
    "other",
    "unknown",
)
ENTITY_STATUSES = ("active", "merged", "deletion_pending", "deleted")
MENTION_RESOLUTION_STATUSES = ("unresolved", "resolved", "ambiguous", "needs_review")
ENTITY_RESOLUTION_OUTCOMES = (
    "matched_existing",
    "created_new",
    "left_unresolved",
    "sent_to_review",
    "corrected",
    "reassigned",
    "merged",
)
ENTITY_RELATIONSHIP_TYPES = (
    "works_at",
    "member_of",
    "reports_to",
    "knows",
    "part_of",
    "located_in",
    "uses",
    "acquired_by",
    "merged_into",
    "renamed_to",
    "related_to",
)
MEMORY_RELATIONSHIP_TYPES = (
    "supports",
    "contradicts",
    "supersedes",
    "updates",
    "part_of",
    "derived_from",
    "depends_on",
    "related_to",
)
SUPERSESSION_REASONS = ("temporal_change", "replacement", "correction")
MEMORY_ENTITY_ROLES = ("subject", "object", "mentioned", "context")
PROVENANCE_ORIGIN_KINDS = ("explicit", "inferred", "system_generated")

MENTION_OUTCOMES = (
    "'matched_existing', 'created_new', 'left_unresolved', 'sent_to_review',"
    " 'corrected', 'reassigned'"
)
ASSIGNING_OUTCOMES = "'matched_existing', 'created_new', 'corrected', 'reassigned', 'merged'"
CHANGING_OUTCOMES = "'corrected', 'reassigned', 'merged'"
SYMMETRIC_ENTITY_TYPES = "'knows', 'related_to'"
SYMMETRIC_MEMORY_TYPES = "'contradicts', 'related_to'"
PREVIOUS_DIFFERS = "previous_entity_id IS NULL OR previous_entity_id IS DISTINCT FROM entity_id"

GUARDED_TABLES: dict[str, tuple[str, ...]] = {
    "pm_entity": (
        "entity_type",
        "canonical_name",
        "normalized_name",
        "status",
        "merged_into_id",
        "updated_at",
    ),
    "pm_entity_alias": (),
    "pm_entity_mention": ("resolution_status", "entity_id", "confidence", "updated_at"),
    "pm_entity_resolution": (),
    "pm_entity_relationship": ("valid_to", "superseded_at", "updated_at"),
    "pm_memory_relationship": ("valid_to", "superseded_at", "updated_at"),
    "pm_memory_entity": (),
}


def memory_schema() -> str:
    schema = context.config.attributes["memory_schema"]
    if not isinstance(schema, str):
        raise TypeError("memory_schema must be set by migrations/env.py")
    return schema


def _in(column: str, values: Sequence[str]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


def _ck(table: str, name: str, condition: str) -> sa.CheckConstraint:
    return sa.CheckConstraint(condition, name=op.f(f"ck_{table}_{name}"))


def _owner_fk(table: str, column: str, target: str, schema: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        [column, "owner_id"],
        [f"{schema}.{target}.id", f"{schema}.{target}.owner_id"],
        name=op.f(f"fk_{table}_{column}_{target}"),
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


def _index(table: str, columns: list[str], schema: str) -> None:
    op.create_index(op.f(f"ix_{table}_{'_'.join(columns)}"), table, columns, schema=schema)


def _temporal(table: str) -> list[sa.CheckConstraint]:
    return [
        _ck(
            table,
            "valid_interval",
            "valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from",
        ),
        _ck(
            table,
            "superseded_after_recorded",
            "superseded_at IS NULL OR superseded_at >= recorded_at",
        ),
    ]


def _temporal_columns() -> list[sa.Column[object]]:
    return [
        sa.Column("confidence", sa.Double()),
        sa.Column("valid_from", sa.DateTime(timezone=True)),
        sa.Column("valid_to", sa.DateTime(timezone=True)),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("superseded_at", sa.DateTime(timezone=True)),
    ]


def upgrade() -> None:
    schema = memory_schema()

    t = "pm_entity"
    op.create_table(
        t,
        sa.Column("id", sa.Uuid()),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("scope", sa.String(16), nullable=False),
        sa.Column("entity_type", sa.String(32), nullable=False),
        sa.Column("canonical_name", sa.Text(), nullable=False),
        sa.Column("normalized_name", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("merged_into_id", sa.Uuid()),
        _created(),
        _updated(),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{t}")),
        sa.UniqueConstraint("id", "owner_id", name=op.f(f"uq_{t}_id_owner_id")),
        _owner_fk(t, "merged_into_id", "pm_entity", schema),
        _ck(t, "scope", _in("scope", ENTITY_SCOPES)),
        _ck(t, "private_only", "scope = 'private'"),
        _ck(t, "entity_type", _in("entity_type", ENTITY_TYPES)),
        _ck(t, "status", _in("status", ENTITY_STATUSES)),
        _ck(t, "merged_target", "(status = 'merged') = (merged_into_id IS NOT NULL)"),
        _ck(t, "not_merged_into_self", "merged_into_id IS DISTINCT FROM id"),
        _ck(t, "canonical_name", "length(btrim(canonical_name)) > 0"),
        _ck(t, "normalized_name", "length(normalized_name) > 0"),
        schema=schema,
    )
    _index(t, ["owner_id", "normalized_name"], schema)

    t = "pm_entity_alias"
    op.create_table(
        t,
        sa.Column("id", sa.Uuid()),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("alias", sa.Text(), nullable=False),
        sa.Column("normalized_alias", sa.Text(), nullable=False),
        sa.Column("source_id", sa.Uuid()),
        _created(),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{t}")),
        sa.UniqueConstraint(
            "entity_id", "normalized_alias", name=op.f(f"uq_{t}_entity_id_normalized_alias")
        ),
        _owner_fk(t, "entity_id", "pm_entity", schema),
        _owner_fk(t, "source_id", "pm_memory_source", schema),
        _ck(t, "alias", "length(btrim(alias)) > 0"),
        _ck(t, "normalized_alias", "length(normalized_alias) > 0"),
        schema=schema,
    )
    _index(t, ["owner_id", "normalized_alias"], schema)

    t = "pm_entity_mention"
    op.create_table(
        t,
        sa.Column("id", sa.Uuid()),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("candidate_id", sa.Uuid()),
        sa.Column("mention_text", sa.Text(), nullable=False),
        sa.Column("mention_type", sa.String(32), nullable=False),
        sa.Column("resolution_status", sa.String(32), nullable=False),
        sa.Column("entity_id", sa.Uuid()),
        sa.Column("confidence", sa.Double()),
        sa.Column("start_offset", sa.Integer()),
        sa.Column("end_offset", sa.Integer()),
        sa.Column("context", postgresql.JSONB(), server_default="{}", nullable=False),
        _created(),
        _updated(),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{t}")),
        sa.UniqueConstraint("id", "owner_id", name=op.f(f"uq_{t}_id_owner_id")),
        _owner_fk(t, "source_id", "pm_memory_source", schema),
        _owner_fk(t, "candidate_id", "pm_memory_candidate", schema),
        _owner_fk(t, "entity_id", "pm_entity", schema),
        _ck(t, "mention_type", _in("mention_type", ENTITY_TYPES)),
        _ck(t, "resolution_status", _in("resolution_status", MENTION_RESOLUTION_STATUSES)),
        _ck(t, "resolved_entity", "(resolution_status = 'resolved') = (entity_id IS NOT NULL)"),
        _ck(t, "mention_text", "length(btrim(mention_text)) > 0"),
        _ck(t, "start_offset", "start_offset IS NULL OR start_offset >= 0"),
        _ck(
            t,
            "end_offset",
            "end_offset IS NULL OR (start_offset IS NOT NULL AND end_offset >= start_offset)",
        ),
        _score(t, "confidence"),
        schema=schema,
    )
    _index(t, ["owner_id", "entity_id"], schema)
    _index(t, ["owner_id", "source_id"], schema)

    t = "pm_entity_resolution"
    op.create_table(
        t,
        sa.Column("id", sa.Uuid()),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("seq", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("outcome", sa.String(32), nullable=False),
        sa.Column("mention_id", sa.Uuid()),
        sa.Column("entity_id", sa.Uuid()),
        sa.Column("previous_entity_id", sa.Uuid()),
        sa.Column("candidate_entity_ids", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("rationale", sa.Text()),
        sa.Column("evidence", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        _created(),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{t}")),
        _owner_fk(t, "mention_id", "pm_entity_mention", schema),
        _owner_fk(t, "entity_id", "pm_entity", schema),
        _owner_fk(t, "previous_entity_id", "pm_entity", schema),
        _ck(t, "outcome", _in("outcome", ENTITY_RESOLUTION_OUTCOMES)),
        _ck(t, "mention_ref", f"(outcome IN ({MENTION_OUTCOMES})) = (mention_id IS NOT NULL)"),
        _ck(t, "entity_ref", f"(outcome IN ({ASSIGNING_OUTCOMES})) = (entity_id IS NOT NULL)"),
        _ck(
            t,
            "previous_ref",
            f"(outcome IN ({CHANGING_OUTCOMES})) = (previous_entity_id IS NOT NULL)",
        ),
        _ck(t, "previous_differs", PREVIOUS_DIFFERS),
        _ck(t, "candidates_array", "jsonb_typeof(candidate_entity_ids) = 'array'"),
        schema=schema,
    )
    _index(t, ["owner_id", "mention_id"], schema)
    _index(t, ["owner_id", "entity_id"], schema)

    t = "pm_entity_relationship"
    op.create_table(
        t,
        sa.Column("id", sa.Uuid()),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("source_entity_id", sa.Uuid(), nullable=False),
        sa.Column("target_entity_id", sa.Uuid(), nullable=False),
        sa.Column("relationship_type", sa.String(32), nullable=False),
        sa.Column("origin_kind", sa.String(32), nullable=False),
        *_temporal_columns(),
        sa.Column("source_id", sa.Uuid()),
        _created(),
        _updated(),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{t}")),
        _owner_fk(t, "source_entity_id", "pm_entity", schema),
        _owner_fk(t, "target_entity_id", "pm_entity", schema),
        _owner_fk(t, "source_id", "pm_memory_source", schema),
        _ck(t, "relationship_type", _in("relationship_type", ENTITY_RELATIONSHIP_TYPES)),
        _ck(t, "origin_kind", _in("origin_kind", PROVENANCE_ORIGIN_KINDS)),
        _ck(t, "distinct_endpoints", "source_entity_id <> target_entity_id"),
        _ck(
            t,
            "symmetric_order",
            f"relationship_type NOT IN ({SYMMETRIC_ENTITY_TYPES})"
            " OR source_entity_id < target_entity_id",
        ),
        *_temporal(t),
        _score(t, "confidence"),
        schema=schema,
    )
    op.create_index(
        op.f("uq_pm_entity_relationship_current"),
        t,
        ["source_entity_id", "target_entity_id", "relationship_type"],
        unique=True,
        schema=schema,
        postgresql_where=sa.text("superseded_at IS NULL"),
    )
    _index(t, ["owner_id", "source_entity_id"], schema)
    _index(t, ["owner_id", "target_entity_id"], schema)

    t = "pm_memory_relationship"
    op.create_table(
        t,
        sa.Column("id", sa.Uuid()),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("source_memory_id", sa.Uuid(), nullable=False),
        sa.Column("target_memory_id", sa.Uuid(), nullable=False),
        sa.Column("relationship_type", sa.String(32), nullable=False),
        sa.Column("reason", sa.String(32)),
        sa.Column("origin_kind", sa.String(32), nullable=False),
        *_temporal_columns(),
        _created(),
        _updated(),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{t}")),
        _owner_fk(t, "source_memory_id", "pm_atomic_memory", schema),
        _owner_fk(t, "target_memory_id", "pm_atomic_memory", schema),
        _ck(t, "relationship_type", _in("relationship_type", MEMORY_RELATIONSHIP_TYPES)),
        _ck(t, "origin_kind", _in("origin_kind", PROVENANCE_ORIGIN_KINDS)),
        _ck(t, "reason", f"reason IS NULL OR {_in('reason', SUPERSESSION_REASONS)}"),
        _ck(t, "reason_required", "(relationship_type = 'supersedes') = (reason IS NOT NULL)"),
        _ck(t, "distinct_endpoints", "source_memory_id <> target_memory_id"),
        _ck(
            t,
            "symmetric_order",
            f"relationship_type NOT IN ({SYMMETRIC_MEMORY_TYPES})"
            " OR source_memory_id < target_memory_id",
        ),
        *_temporal(t),
        _score(t, "confidence"),
        schema=schema,
    )
    op.create_index(
        op.f("uq_pm_memory_relationship_current"),
        t,
        ["source_memory_id", "target_memory_id", "relationship_type"],
        unique=True,
        schema=schema,
        postgresql_where=sa.text("superseded_at IS NULL"),
    )
    _index(t, ["owner_id", "source_memory_id"], schema)
    _index(t, ["owner_id", "target_memory_id"], schema)

    t = "pm_memory_entity"
    op.create_table(
        t,
        sa.Column("id", sa.Uuid()),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("memory_id", sa.Uuid(), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        _created(),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{t}")),
        sa.UniqueConstraint(
            "memory_id", "entity_id", "role", name=op.f(f"uq_{t}_memory_id_entity_id_role")
        ),
        _owner_fk(t, "memory_id", "pm_atomic_memory", schema),
        _owner_fk(t, "entity_id", "pm_entity", schema),
        _ck(t, "role", _in("role", MEMORY_ENTITY_ROLES)),
        schema=schema,
    )
    _index(t, ["owner_id", "entity_id"], schema)

    for table, mutable in GUARDED_TABLES.items():
        arguments = ", ".join(f"'{column}'" for column in mutable)
        op.execute(
            f'CREATE TRIGGER {table}_guard BEFORE UPDATE ON "{schema}".{table} '
            f'FOR EACH ROW EXECUTE FUNCTION "{schema}".me_guard_columns({arguments})'
        )


def downgrade() -> None:
    # Destructive: drops all entity and relationship data in this schema. Never
    # run against real data without a verified backup.
    schema = memory_schema()
    for table in GUARDED_TABLES:
        op.execute(f'DROP TRIGGER IF EXISTS {table}_guard ON "{schema}".{table}')
    for table in (
        "pm_memory_entity",
        "pm_memory_relationship",
        "pm_entity_relationship",
        "pm_entity_resolution",
        "pm_entity_mention",
        "pm_entity_alias",
        "pm_entity",
    ):
        op.drop_table(table, schema=schema)
