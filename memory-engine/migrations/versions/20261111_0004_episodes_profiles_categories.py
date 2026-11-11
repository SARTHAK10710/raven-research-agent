"""Episodes, profiles, categories and memory embedding metadata (Phase 8.2 step 4).

Creates pm_episode, pm_episode_membership, pm_episode_event, pm_profile,
pm_profile_revision, pm_profile_memory, pm_profile_refresh, pm_memory_category
and pm_memory_embedding. No consolidation-result table: established outputs
are episodes and profiles (Decision 5.4.23; 7.1 section 23 note).

* pm_profile <-> pm_profile_revision reference each other; the profile's key to
  its current revision is DEFERRABLE INITIALLY DEFERRED (repositories force the
  check immediately after writing).
* me_guard_columns (from 0002) limits updates: revisions, supports and refresh
  history are append-only; memberships, events and categories can only be
  closed; episodes, profiles and embeddings change only their state columns.

Vocabularies and rule texts are FROZEN here; unit tests compare them with the
domain enums and the models.

Revision ID: 0004_episodes_profiles
Revises: 0003_entities_and_relationships
Create Date: 2026-11-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op
from sqlalchemy.dialects import postgresql

revision: str = "0004_episodes_profiles"
down_revision: str | None = "0003_entities_and_relationships"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EPISODE_STATUSES = ("active", "needs_refresh", "needs_review", "deletion_pending", "deleted")
TEMPORAL_PRECISIONS = ("exact", "day", "month", "year", "approximate", "unknown")
PROFILE_TYPES = (
    "user",
    "preference",
    "project",
    "skill_knowledge",
    "relationship_context",
    "work_context",
)
PROFILE_STATUSES = (
    "current",
    "stale",
    "refreshing",
    "refresh_failed",
    "needs_review",
    "deletion_pending",
    "deleted",
)
REFRESH_TRIGGERS = ("event", "scheduled", "on_demand")
REFRESH_OUTCOMES = ("refreshed", "no_change", "partially_refreshed", "failed", "needs_review")
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
MEMORY_ORIGINS = ("explicit", "inferred")
EMBEDDING_PURPOSES = ("primary", "aspect")
EMBEDDING_STATUSES = (
    "pending",
    "generating",
    "generated",
    "indexing",
    "indexed",
    "failed",
    "superseded",
    "deletion_pending",
)

REVISION_OUTCOMES = "'refreshed', 'partially_refreshed'"
SAFE_ERROR_CODE = "error_code IS NULL OR error_code ~ '^[A-Z][A-Z0-9_]{0,63}$'"

GUARDED_TABLES: dict[str, tuple[str, ...]] = {
    "pm_episode": (
        "title",
        "summary",
        "status",
        "starts_at",
        "start_precision",
        "ends_at",
        "end_precision",
        "method_version",
        "updated_at",
    ),
    "pm_episode_membership": ("removed_at", "updated_at"),
    "pm_episode_event": ("superseded_at", "updated_at"),
    "pm_profile": ("status", "current_revision_number", "refreshed_at", "updated_at"),
    "pm_profile_revision": (),
    "pm_profile_memory": (),
    "pm_profile_refresh": (),
    "pm_memory_category": ("superseded_at", "updated_at"),
    "pm_memory_embedding": ("status", "updated_at"),
}


def memory_schema() -> str:
    schema = context.config.attributes["memory_schema"]
    if not isinstance(schema, str):
        raise TypeError("memory_schema must be set by migrations/env.py")
    return schema


def _in(column: str, values: Sequence[str]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


def _precise(column: str, precision: str) -> str:
    return f"({precision} = 'unknown') = ({column} IS NULL)"


def _ck(table: str, name: str, condition: str) -> sa.CheckConstraint:
    return sa.CheckConstraint(condition, name=op.f(f"ck_{table}_{name}"))


def _owner_fk(table: str, column: str, target: str, schema: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        [column, "owner_id"],
        [f"{schema}.{target}.id", f"{schema}.{target}.owner_id"],
        name=op.f(f"fk_{table}_{column}_{target}"),
        ondelete="RESTRICT",
    )


def _memory_revision_fk(table: str, column: str, schema: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["memory_id", column],
        [
            f"{schema}.pm_atomic_memory_revision.memory_id",
            f"{schema}.pm_atomic_memory_revision.revision_number",
        ],
        name=op.f(f"fk_{table}_memory_id_pm_atomic_memory_revision"),
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


def _index(table: str, columns: list[str], schema: str) -> None:
    op.create_index(op.f(f"ix_{table}_{'_'.join(columns)}"), table, columns, schema=schema)


def _partial_unique(name: str, table: str, columns: list[str], where: str, schema: str) -> None:
    op.create_index(
        op.f(name),
        table,
        columns,
        unique=True,
        schema=schema,
        postgresql_where=sa.text(where),
    )


def upgrade() -> None:
    schema = memory_schema()

    t = "pm_episode"
    op.create_table(
        t,
        sa.Column("id", sa.Uuid()),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.Text()),
        sa.Column("summary", sa.Text()),
        sa.Column("status", sa.String(32), nullable=False),
        _ts("starts_at"),
        sa.Column("start_precision", sa.String(16), nullable=False),
        _ts("ends_at"),
        sa.Column("end_precision", sa.String(16), nullable=False),
        sa.Column("method", sa.Text(), nullable=False),
        sa.Column("method_version", sa.Text(), nullable=False),
        _ts("recorded_at", nullable=False),
        _created(),
        _updated(),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{t}")),
        sa.UniqueConstraint("id", "owner_id", name=op.f(f"uq_{t}_id_owner_id")),
        _ck(t, "status", _in("status", EPISODE_STATUSES)),
        _ck(t, "start_precision", _in("start_precision", TEMPORAL_PRECISIONS)),
        _ck(t, "end_precision", _in("end_precision", TEMPORAL_PRECISIONS)),
        _ck(t, "start_known", _precise("starts_at", "start_precision")),
        _ck(t, "end_known", _precise("ends_at", "end_precision")),
        _ck(t, "boundaries", "starts_at IS NULL OR ends_at IS NULL OR ends_at >= starts_at"),
        _ck(t, "title", "title IS NULL OR length(btrim(title)) > 0"),
        _ck(t, "method", "length(btrim(method)) > 0"),
        schema=schema,
    )
    _index(t, ["owner_id", "status"], schema)

    t = "pm_episode_membership"
    op.create_table(
        t,
        sa.Column("id", sa.Uuid()),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("episode_id", sa.Uuid(), nullable=False),
        sa.Column("memory_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer()),
        sa.Column("confidence", sa.Double()),
        _ts("added_at", nullable=False),
        _ts("removed_at"),
        _created(),
        _updated(),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{t}")),
        _owner_fk(t, "episode_id", "pm_episode", schema),
        _owner_fk(t, "memory_id", "pm_atomic_memory", schema),
        _ck(t, "sequence", "sequence IS NULL OR sequence >= 0"),
        _ck(t, "removed_after_added", "removed_at IS NULL OR removed_at >= added_at"),
        _score(t, "confidence"),
        schema=schema,
    )
    _partial_unique(
        "uq_pm_episode_membership_current",
        t,
        ["episode_id", "memory_id"],
        "removed_at IS NULL",
        schema,
    )
    _index(t, ["owner_id", "memory_id"], schema)

    t = "pm_episode_event"
    op.create_table(
        t,
        sa.Column("id", sa.Uuid()),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("episode_id", sa.Uuid(), nullable=False),
        sa.Column("memory_id", sa.Uuid()),
        sa.Column("label", sa.Text(), nullable=False),
        _ts("occurred_at"),
        sa.Column("precision", sa.String(16), nullable=False),
        _ts("recorded_at", nullable=False),
        _ts("superseded_at"),
        _created(),
        _updated(),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{t}")),
        _owner_fk(t, "episode_id", "pm_episode", schema),
        _owner_fk(t, "memory_id", "pm_atomic_memory", schema),
        _ck(t, "precision", _in("precision", TEMPORAL_PRECISIONS)),
        _ck(t, "occurred_known", _precise("occurred_at", "precision")),
        _ck(t, "label", "length(btrim(label)) > 0"),
        _ck(
            t,
            "superseded_after_recorded",
            "superseded_at IS NULL OR superseded_at >= recorded_at",
        ),
        schema=schema,
    )
    _index(t, ["owner_id", "episode_id"], schema)

    t = "pm_profile"
    op.create_table(
        t,
        sa.Column("id", sa.Uuid()),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("profile_type", sa.String(32), nullable=False),
        sa.Column("subject_entity_id", sa.Uuid()),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("current_revision_number", sa.Integer(), nullable=False),
        _ts("refreshed_at", nullable=False),
        _created(),
        _updated(),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{t}")),
        sa.UniqueConstraint("id", "owner_id", name=op.f(f"uq_{t}_id_owner_id")),
        _owner_fk(t, "subject_entity_id", "pm_entity", schema),
        _ck(t, "profile_type", _in("profile_type", PROFILE_TYPES)),
        _ck(t, "status", _in("status", PROFILE_STATUSES)),
        _ck(t, "revision_number_positive", "current_revision_number >= 1"),
        schema=schema,
    )
    _partial_unique(
        "uq_pm_profile_one_per_type",
        t,
        ["owner_id", "profile_type"],
        "subject_entity_id IS NULL AND status <> 'deleted'",
        schema,
    )
    _partial_unique(
        "uq_pm_profile_one_per_subject",
        t,
        ["owner_id", "profile_type", "subject_entity_id"],
        "subject_entity_id IS NOT NULL AND status <> 'deleted'",
        schema,
    )

    t = "pm_profile_revision"
    op.create_table(
        t,
        sa.Column("id", sa.Uuid()),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("attributes", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("method", sa.Text(), nullable=False),
        sa.Column("method_version", sa.Text(), nullable=False),
        _ts("recorded_at", nullable=False),
        _created(),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{t}")),
        sa.UniqueConstraint(
            "profile_id", "revision_number", name=op.f(f"uq_{t}_profile_id_revision_number")
        ),
        _owner_fk(t, "profile_id", "pm_profile", schema),
        _ck(t, "revision_number_positive", "revision_number >= 1"),
        _ck(t, "method", "length(btrim(method)) > 0"),
        schema=schema,
    )
    op.create_foreign_key(
        op.f("fk_pm_profile_id_pm_profile_revision"),
        "pm_profile",
        "pm_profile_revision",
        ["id", "current_revision_number"],
        ["profile_id", "revision_number"],
        source_schema=schema,
        referent_schema=schema,
        ondelete="RESTRICT",
        deferrable=True,
        initially="DEFERRED",
    )

    t = "pm_profile_memory"
    op.create_table(
        t,
        sa.Column("id", sa.Uuid()),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("memory_id", sa.Uuid(), nullable=False),
        sa.Column("memory_revision_number", sa.Integer(), nullable=False),
        sa.Column("attribute", sa.Text()),
        sa.Column("relevance", sa.Double()),
        _created(),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{t}")),
        _owner_fk(t, "profile_id", "pm_profile", schema),
        sa.ForeignKeyConstraint(
            ["profile_id", "revision_number"],
            [
                f"{schema}.pm_profile_revision.profile_id",
                f"{schema}.pm_profile_revision.revision_number",
            ],
            name=op.f(f"fk_{t}_profile_id_pm_profile_revision"),
            ondelete="RESTRICT",
        ),
        _owner_fk(t, "memory_id", "pm_atomic_memory", schema),
        _memory_revision_fk(t, "memory_revision_number", schema),
        _ck(t, "attribute", "attribute IS NULL OR length(btrim(attribute)) > 0"),
        _score(t, "relevance"),
        schema=schema,
    )
    _index(t, ["owner_id", "memory_id"], schema)
    _index(t, ["profile_id", "revision_number"], schema)

    t = "pm_profile_refresh"
    op.create_table(
        t,
        sa.Column("id", sa.Uuid()),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("seq", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("trigger", sa.String(16), nullable=False),
        sa.Column("outcome", sa.String(32), nullable=False),
        sa.Column("from_revision", sa.Integer(), nullable=False),
        sa.Column("to_revision", sa.Integer()),
        sa.Column("error_code", sa.String(64)),
        _ts("recorded_at", nullable=False),
        _created(),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{t}")),
        _owner_fk(t, "profile_id", "pm_profile", schema),
        _ck(t, "trigger", _in("trigger", REFRESH_TRIGGERS)),
        _ck(t, "outcome", _in("outcome", REFRESH_OUTCOMES)),
        _ck(
            t,
            "revision_matches_outcome",
            f"(outcome IN ({REVISION_OUTCOMES})) = (to_revision IS NOT NULL)",
        ),
        _ck(t, "next_revision", "to_revision IS NULL OR to_revision = from_revision + 1"),
        _ck(t, "failure_code", "(outcome = 'failed') = (error_code IS NOT NULL)"),
        _ck(t, "error_code", SAFE_ERROR_CODE),
        schema=schema,
    )
    _index(t, ["owner_id", "profile_id"], schema)

    t = "pm_memory_category"
    op.create_table(
        t,
        sa.Column("id", sa.Uuid()),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("memory_id", sa.Uuid(), nullable=False),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("origin", sa.String(32), nullable=False),
        sa.Column("confidence", sa.Double()),
        _ts("recorded_at", nullable=False),
        _ts("superseded_at"),
        _created(),
        _updated(),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{t}")),
        _owner_fk(t, "memory_id", "pm_atomic_memory", schema),
        _ck(t, "category", _in("category", MEMORY_CATEGORIES)),
        _ck(t, "origin", _in("origin", MEMORY_ORIGINS)),
        _ck(
            t,
            "superseded_after_recorded",
            "superseded_at IS NULL OR superseded_at >= recorded_at",
        ),
        _score(t, "confidence"),
        schema=schema,
    )
    _partial_unique(
        "uq_pm_memory_category_current",
        t,
        ["memory_id", "category"],
        "superseded_at IS NULL",
        schema,
    )
    _index(t, ["owner_id", "category"], schema)

    t = "pm_memory_embedding"
    op.create_table(
        t,
        sa.Column("id", sa.Uuid()),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("memory_id", sa.Uuid(), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("purpose", sa.String(16), nullable=False),
        sa.Column("aspect_label", sa.Text()),
        sa.Column("model_id", sa.Text(), nullable=False),
        sa.Column("model_revision", sa.Text(), nullable=False),
        sa.Column("dimensions", sa.Integer(), nullable=False),
        sa.Column("preprocessing_version", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        _created(),
        _updated(),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{t}")),
        _owner_fk(t, "memory_id", "pm_atomic_memory", schema),
        _memory_revision_fk(t, "revision_number", schema),
        _ck(t, "purpose", _in("purpose", EMBEDDING_PURPOSES)),
        _ck(t, "status", _in("status", EMBEDDING_STATUSES)),
        _ck(t, "aspect_label", "(purpose = 'aspect') = (aspect_label IS NOT NULL)"),
        _ck(t, "dimensions", "dimensions > 0"),
        schema=schema,
    )
    _partial_unique(
        "uq_pm_memory_embedding_primary",
        t,
        ["memory_id", "revision_number", "model_id", "model_revision", "preprocessing_version"],
        "purpose = 'primary'",
        schema,
    )
    _partial_unique(
        "uq_pm_memory_embedding_aspect",
        t,
        [
            "memory_id",
            "revision_number",
            "model_id",
            "model_revision",
            "preprocessing_version",
            "aspect_label",
        ],
        "purpose = 'aspect'",
        schema,
    )
    _index(t, ["owner_id", "memory_id"], schema)

    for table, mutable in GUARDED_TABLES.items():
        arguments = ", ".join(f"'{column}'" for column in mutable)
        op.execute(
            f'CREATE TRIGGER {table}_guard BEFORE UPDATE ON "{schema}".{table} '
            f'FOR EACH ROW EXECUTE FUNCTION "{schema}".me_guard_columns({arguments})'
        )


def downgrade() -> None:
    # Destructive: drops all episodes, profiles, categories and memory embedding
    # metadata in this schema. Never run against real data without a backup.
    schema = memory_schema()
    for table in GUARDED_TABLES:
        op.execute(f'DROP TRIGGER IF EXISTS {table}_guard ON "{schema}".{table}')
    op.drop_constraint(
        op.f("fk_pm_profile_id_pm_profile_revision"),
        "pm_profile",
        schema=schema,
        type_="foreignkey",
    )
    for table in (
        "pm_memory_embedding",
        "pm_memory_category",
        "pm_profile_refresh",
        "pm_profile_memory",
        "pm_profile_revision",
        "pm_profile",
        "pm_episode_event",
        "pm_episode_membership",
        "pm_episode",
    ):
        op.drop_table(table, schema=schema)
