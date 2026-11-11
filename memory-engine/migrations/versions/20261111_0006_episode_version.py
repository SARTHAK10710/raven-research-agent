"""Optimistic concurrency for episodes (Phase 8.2 acceptance review, item A1).

Adds ``pm_episode.version``. Episode updates replace title, summary and
boundaries; without a version, two writers that read the same episode could
both succeed and the second would silently overwrite the first (7.2 section 7;
7.1 section 23.2). Existing rows start at version 1.

The episode guard trigger (0004) lists its mutable columns, so it is recreated
with ``version`` added.

Revision ID: 0006_episode_version
Revises: 0005_processing_deletion
Create Date: 2026-11-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op

revision: str = "0006_episode_version"
down_revision: str | None = "0005_processing_deletion"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# FROZEN: the episode's mutable columns before (0004) and after this migration.
EPISODE_MUTABLE_0004 = (
    "title",
    "summary",
    "status",
    "starts_at",
    "start_precision",
    "ends_at",
    "end_precision",
    "method_version",
    "updated_at",
)
GUARDED_TABLES: dict[str, tuple[str, ...]] = {
    "pm_episode": (*EPISODE_MUTABLE_0004, "version"),
}


def memory_schema() -> str:
    schema = context.config.attributes["memory_schema"]
    if not isinstance(schema, str):
        raise TypeError("memory_schema must be set by migrations/env.py")
    return schema


def _guard(schema: str, mutable: Sequence[str]) -> None:
    arguments = ", ".join(f"'{column}'" for column in mutable)
    op.execute(f'DROP TRIGGER IF EXISTS pm_episode_guard ON "{schema}".pm_episode')
    op.execute(
        f'CREATE TRIGGER pm_episode_guard BEFORE UPDATE ON "{schema}".pm_episode '
        f'FOR EACH ROW EXECUTE FUNCTION "{schema}".me_guard_columns({arguments})'
    )


def upgrade() -> None:
    schema = memory_schema()
    op.add_column(
        "pm_episode",
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        schema=schema,
    )
    op.create_check_constraint(
        op.f("ck_pm_episode_version_positive"), "pm_episode", "version >= 1", schema=schema
    )
    _guard(schema, GUARDED_TABLES["pm_episode"])


def downgrade() -> None:
    schema = memory_schema()
    _guard(schema, EPISODE_MUTABLE_0004)
    op.drop_constraint(
        op.f("ck_pm_episode_version_positive"), "pm_episode", schema=schema, type_="check"
    )
    op.drop_column("pm_episode", "version", schema=schema)
