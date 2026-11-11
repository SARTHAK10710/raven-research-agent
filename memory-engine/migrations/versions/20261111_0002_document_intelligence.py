"""Document Intelligence tables and the document-evidence path (Phase 8.2 step 2).

Creates doc_document, doc_document_version, doc_extracted_representation,
doc_chunk (with a 'simple' full-text vector and GIN index), doc_chunk_location,
doc_embedding (metadata only; vectors arrive in 8.7) and
doc_processing_operation; adds pm_document_evidence_ref and lets pm_provenance
cite it.

Column guards: me_guard_columns(<mutable columns...>) rejects any UPDATE that
changes a column not listed; with no arguments the table is append-only.

Vocabularies are FROZEN here as literals (see 0001); a unit test keeps them
equal to the domain enums.

Revision ID: 0002_document_intelligence
Revises: 0001_personal_memory_core
Create Date: 2026-11-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op
from sqlalchemy.dialects import postgresql

revision: str = "0002_document_intelligence"
down_revision: str | None = "0001_personal_memory_core"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DOCUMENT_MEDIA_TYPES = (
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
)
DOCUMENT_LIFECYCLE_STATUSES = (
    "registered",
    "available",
    "deletion_requested",
    "deleting",
    "deleted",
)
VERSION_PROCESSING_STATUSES = (
    "registered",
    "validated",
    "stored",
    "parsing",
    "extracted",
    "chunked",
    "embedded",
    "indexed",
    "validation_failed",
    "extraction_failed",
    "processing_failed",
    "retry_pending",
    "deletion_requested",
    "deleting",
    "deleted",
)
EXTRACTION_STATUSES = ("extracted", "partially_extracted", "extraction_failed")
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
OPERATION_TYPES = (
    "validation",
    "storage",
    "extraction",
    "structure_extraction",
    "normalization",
    "chunking",
    "embedding",
    "indexing",
    "deletion",
)
OPERATION_STATUSES = (
    "created",
    "queued",
    "running",
    "completed",
    "failed",
    "retry_pending",
    "cancellation_requested",
    "cancelled",
)
DOCUMENT_EVIDENCE_STATUSES = ("active", "source_deleted")

SHA256 = "~ '^[0-9a-f]{64}$'"
SAFE_ERROR_CODE = "error_code IS NULL OR error_code ~ '^[A-Z][A-Z0-9_]{0,63}$'"
EVIDENCE_LINKS_MATCH_STATUS = (
    "(status = 'active' AND document_id IS NOT DISTINCT FROM document_ref"
    " AND version_id IS NOT DISTINCT FROM version_ref"
    " AND chunk_id IS NOT DISTINCT FROM chunk_ref)"
    " OR (status = 'source_deleted' AND document_id IS NULL AND version_id IS NULL"
    " AND chunk_id IS NULL)"
)
OLD_PROVENANCE_EVIDENCE = "source_id IS NOT NULL OR candidate_id IS NOT NULL"
PROVENANCE_REFERENCES_EVIDENCE = (
    "source_id IS NOT NULL OR candidate_id IS NOT NULL OR document_evidence_id IS NOT NULL"
)

# table -> columns that may change after insert (empty: append-only)
GUARDED_TABLES: dict[str, tuple[str, ...]] = {
    "doc_document": ("title", "lifecycle_status", "current_version_id", "updated_at"),
    "doc_document_version": ("processing_status", "updated_at"),
    "doc_extracted_representation": (),
    "doc_chunk": (),
    "doc_chunk_location": (),
    "doc_embedding": ("status", "updated_at"),
    "doc_processing_operation": ("status", "attempts", "error_code", "updated_at"),
    "pm_document_evidence_ref": (
        "status",
        "document_id",
        "version_id",
        "chunk_id",
        "updated_at",
    ),
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


def _fk(
    table: str, columns: list[str], target: str, target_columns: list[str], schema: str
) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        columns,
        [f"{schema}.{target}.{column}" for column in target_columns],
        name=op.f(f"fk_{table}_{columns[0]}_{target}"),
        ondelete="RESTRICT",
    )


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


def upgrade() -> None:
    schema = memory_schema()

    t = "doc_document"
    op.create_table(
        t,
        sa.Column("id", sa.Uuid()),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.Text()),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("media_type", sa.String(100), nullable=False),
        sa.Column("lifecycle_status", sa.String(32), nullable=False),
        sa.Column("current_version_id", sa.Uuid()),
        _created(),
        _updated(),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{t}")),
        sa.UniqueConstraint("id", "owner_id", name=op.f(f"uq_{t}_id_owner_id")),
        _ck(t, "media_type", _in("media_type", DOCUMENT_MEDIA_TYPES)),
        _ck(t, "lifecycle_status", _in("lifecycle_status", DOCUMENT_LIFECYCLE_STATUSES)),
        _ck(t, "original_filename", "length(btrim(original_filename)) > 0"),
        _ck(t, "title", "title IS NULL OR length(btrim(title)) > 0"),
        schema=schema,
    )
    _index(t, ["owner_id", "lifecycle_status"], schema)

    t = "doc_document_version"
    op.create_table(
        t,
        sa.Column("id", sa.Uuid()),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("object_key", sa.Text(), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("media_type", sa.String(100), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processing_status", sa.String(32), nullable=False),
        _created(),
        _updated(),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{t}")),
        sa.UniqueConstraint("id", "owner_id", name=op.f(f"uq_{t}_id_owner_id")),
        sa.UniqueConstraint("id", "document_id", name=op.f(f"uq_{t}_id_document_id")),
        sa.UniqueConstraint(
            "document_id", "version_number", name=op.f(f"uq_{t}_document_id_version_number")
        ),
        sa.UniqueConstraint("object_key", name=op.f(f"uq_{t}_object_key")),
        _fk(t, ["document_id", "owner_id"], "doc_document", ["id", "owner_id"], schema),
        _ck(t, "media_type", _in("media_type", DOCUMENT_MEDIA_TYPES)),
        _ck(t, "processing_status", _in("processing_status", VERSION_PROCESSING_STATUSES)),
        _ck(t, "version_number", "version_number >= 1"),
        _ck(t, "size_bytes", "size_bytes > 0"),
        _ck(t, "content_sha256", f"content_sha256 {SHA256}"),
        _ck(t, "object_key", "length(btrim(object_key)) > 0"),
        schema=schema,
    )
    _index(t, ["owner_id", "document_id"], schema)
    op.create_foreign_key(
        op.f("fk_doc_document_current_version_id_doc_document_version"),
        "doc_document",
        "doc_document_version",
        ["current_version_id", "id"],
        ["id", "document_id"],
        source_schema=schema,
        referent_schema=schema,
        ondelete="RESTRICT",
    )

    t = "doc_extracted_representation"
    op.create_table(
        t,
        sa.Column("id", sa.Uuid()),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("version_id", sa.Uuid(), nullable=False),
        sa.Column("extraction_method", sa.Text(), nullable=False),
        sa.Column("extraction_version", sa.Text(), nullable=False),
        sa.Column("content_ref", sa.Text()),
        sa.Column("structure", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("error_code", sa.String(64)),
        sa.Column("extracted_at", sa.DateTime(timezone=True), nullable=False),
        _created(),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{t}")),
        sa.UniqueConstraint("id", "version_id", name=op.f(f"uq_{t}_id_version_id")),
        _fk(t, ["version_id", "owner_id"], "doc_document_version", ["id", "owner_id"], schema),
        _ck(t, "status", _in("status", EXTRACTION_STATUSES)),
        _ck(t, "error_code", SAFE_ERROR_CODE),
        _ck(t, "failure_has_code", "(status = 'extraction_failed') = (error_code IS NOT NULL)"),
        schema=schema,
    )
    _index(t, ["owner_id", "version_id"], schema)

    t = "doc_chunk"
    op.create_table(
        t,
        sa.Column("id", sa.Uuid()),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("version_id", sa.Uuid(), nullable=False),
        sa.Column("representation_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("chunking_strategy", sa.Text(), nullable=False),
        sa.Column("chunking_version", sa.Text(), nullable=False),
        sa.Column(
            "tsv",
            postgresql.TSVECTOR(),
            sa.Computed("to_tsvector('simple'::regconfig, content)", persisted=True),
        ),
        _created(),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{t}")),
        sa.UniqueConstraint("id", "version_id", name=op.f(f"uq_{t}_id_version_id")),
        sa.UniqueConstraint(
            "representation_id", "sequence", name=op.f(f"uq_{t}_representation_id_sequence")
        ),
        _fk(t, ["version_id", "owner_id"], "doc_document_version", ["id", "owner_id"], schema),
        _fk(
            t,
            ["representation_id", "version_id"],
            "doc_extracted_representation",
            ["id", "version_id"],
            schema,
        ),
        _ck(t, "sequence", "sequence >= 0"),
        _ck(t, "content", "length(btrim(content)) > 0"),
        _ck(t, "content_sha256", f"content_sha256 {SHA256}"),
        schema=schema,
    )
    _index(t, ["owner_id", "version_id"], schema)
    op.create_index(op.f("ix_doc_chunk_tsv"), t, ["tsv"], schema=schema, postgresql_using="gin")

    t = "doc_chunk_location"
    op.create_table(
        t,
        sa.Column("id", sa.Uuid()),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_id", sa.Uuid(), nullable=False),
        sa.Column("version_id", sa.Uuid(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("page_number", sa.Integer()),
        sa.Column("section_heading", sa.Text()),
        sa.Column("start_offset", sa.Integer()),
        sa.Column("end_offset", sa.Integer()),
        sa.Column("structural_path", postgresql.JSONB()),
        _created(),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{t}")),
        sa.UniqueConstraint("chunk_id", "ordinal", name=op.f(f"uq_{t}_chunk_id_ordinal")),
        _ck(t, "ordinal", "ordinal >= 0"),
        _fk(t, ["chunk_id", "version_id"], "doc_chunk", ["id", "version_id"], schema),
        _fk(t, ["version_id", "owner_id"], "doc_document_version", ["id", "owner_id"], schema),
        _ck(
            t,
            "has_known_field",
            "page_number IS NOT NULL OR section_heading IS NOT NULL"
            " OR start_offset IS NOT NULL OR structural_path IS NOT NULL",
        ),
        _ck(t, "page_number", "page_number IS NULL OR page_number >= 1"),
        _ck(t, "start_offset", "start_offset IS NULL OR start_offset >= 0"),
        _ck(
            t,
            "end_offset",
            "end_offset IS NULL OR (start_offset IS NOT NULL AND end_offset >= start_offset)",
        ),
        schema=schema,
    )
    _index(t, ["owner_id", "chunk_id"], schema)

    t = "doc_embedding"
    op.create_table(
        t,
        sa.Column("id", sa.Uuid()),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_id", sa.Uuid(), nullable=False),
        sa.Column("version_id", sa.Uuid(), nullable=False),
        sa.Column("model_id", sa.Text(), nullable=False),
        sa.Column("model_revision", sa.Text(), nullable=False),
        sa.Column("dimensions", sa.Integer(), nullable=False),
        sa.Column("preprocessing_version", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        _created(),
        _updated(),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{t}")),
        sa.UniqueConstraint(
            "chunk_id",
            "model_id",
            "model_revision",
            "preprocessing_version",
            name=op.f("uq_doc_embedding_chunk_model"),
        ),
        _fk(t, ["chunk_id", "version_id"], "doc_chunk", ["id", "version_id"], schema),
        _fk(t, ["version_id", "owner_id"], "doc_document_version", ["id", "owner_id"], schema),
        _ck(t, "status", _in("status", EMBEDDING_STATUSES)),
        _ck(t, "dimensions", "dimensions > 0"),
        schema=schema,
    )
    _index(t, ["owner_id", "version_id"], schema)

    t = "doc_processing_operation"
    op.create_table(
        t,
        sa.Column("id", sa.Uuid()),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("version_id", sa.Uuid()),
        sa.Column("operation_type", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("idempotency_key", sa.String(200), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_code", sa.String(64)),
        _created(),
        _updated(),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{t}")),
        sa.UniqueConstraint(
            "owner_id", "idempotency_key", name=op.f(f"uq_{t}_owner_id_idempotency_key")
        ),
        _fk(t, ["document_id", "owner_id"], "doc_document", ["id", "owner_id"], schema),
        _fk(
            t,
            ["version_id", "document_id"],
            "doc_document_version",
            ["id", "document_id"],
            schema,
        ),
        _ck(t, "operation_type", _in("operation_type", OPERATION_TYPES)),
        _ck(t, "status", _in("status", OPERATION_STATUSES)),
        _ck(t, "attempts", "attempts >= 0"),
        _ck(t, "error_code", SAFE_ERROR_CODE),
        _ck(t, "idempotency_key", "length(btrim(idempotency_key)) > 0"),
        schema=schema,
    )
    _index(t, ["owner_id", "document_id", "status"], schema)

    t = "pm_document_evidence_ref"
    op.create_table(
        t,
        sa.Column("id", sa.Uuid()),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), nullable=False),
        sa.Column("document_ref", sa.Uuid(), nullable=False),
        sa.Column("version_ref", sa.Uuid(), nullable=False),
        sa.Column("chunk_ref", sa.Uuid()),
        sa.Column("document_id", sa.Uuid()),
        sa.Column("version_id", sa.Uuid()),
        sa.Column("chunk_id", sa.Uuid()),
        sa.Column("extraction_method", sa.Text(), nullable=False),
        sa.Column("page_number", sa.Integer()),
        sa.Column("section_heading", sa.Text()),
        sa.Column("start_offset", sa.Integer()),
        sa.Column("end_offset", sa.Integer()),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        _created(),
        _updated(),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{t}")),
        sa.UniqueConstraint("id", "owner_id", name=op.f(f"uq_{t}_id_owner_id")),
        _fk(t, ["candidate_id", "owner_id"], "pm_memory_candidate", ["id", "owner_id"], schema),
        _fk(t, ["document_id", "owner_id"], "doc_document", ["id", "owner_id"], schema),
        _fk(
            t,
            ["version_id", "document_id"],
            "doc_document_version",
            ["id", "document_id"],
            schema,
        ),
        _fk(t, ["chunk_id", "version_id"], "doc_chunk", ["id", "version_id"], schema),
        _ck(t, "status", _in("status", DOCUMENT_EVIDENCE_STATUSES)),
        _ck(t, "links_match_status", EVIDENCE_LINKS_MATCH_STATUS),
        _ck(t, "extraction_method", "length(btrim(extraction_method)) > 0"),
        _ck(t, "page_number", "page_number IS NULL OR page_number >= 1"),
        _ck(t, "start_offset", "start_offset IS NULL OR start_offset >= 0"),
        _ck(
            t,
            "end_offset",
            "end_offset IS NULL OR (start_offset IS NOT NULL AND end_offset >= start_offset)",
        ),
        schema=schema,
    )
    _index(t, ["owner_id", "document_ref"], schema)
    _index(t, ["owner_id", "candidate_id"], schema)

    # pm_provenance may now cite document evidence. ADD COLUMN does not fire the
    # append-only UPDATE trigger installed by 0001.
    op.add_column("pm_provenance", sa.Column("document_evidence_id", sa.Uuid()), schema=schema)
    op.create_foreign_key(
        op.f("fk_pm_provenance_document_evidence_id_pm_document_evidence_ref"),
        "pm_provenance",
        "pm_document_evidence_ref",
        ["document_evidence_id", "owner_id"],
        ["id", "owner_id"],
        source_schema=schema,
        referent_schema=schema,
        ondelete="RESTRICT",
    )
    op.drop_constraint(op.f("ck_pm_provenance_references_evidence"), "pm_provenance", schema=schema)
    op.create_check_constraint(
        op.f("ck_pm_provenance_references_evidence"),
        "pm_provenance",
        PROVENANCE_REFERENCES_EVIDENCE,
        schema=schema,
    )
    _index("pm_provenance", ["owner_id", "document_evidence_id"], schema)

    op.execute(
        f"""
        CREATE FUNCTION "{schema}".me_guard_columns() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE
            mutable text[] := coalesce(TG_ARGV, '{{}}'::text[]);
        BEGIN
            IF (to_jsonb(NEW) - mutable) IS DISTINCT FROM (to_jsonb(OLD) - mutable) THEN
                RAISE EXCEPTION 'immutable columns of % cannot be updated', TG_TABLE_NAME
                    USING ERRCODE = 'integrity_constraint_violation';
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    for table, mutable in GUARDED_TABLES.items():
        arguments = ", ".join(f"'{column}'" for column in mutable)
        op.execute(
            f'CREATE TRIGGER {table}_guard BEFORE UPDATE ON "{schema}".{table} '
            f'FOR EACH ROW EXECUTE FUNCTION "{schema}".me_guard_columns({arguments})'
        )


def downgrade() -> None:
    # Destructive: drops all Document Intelligence data and document evidence in
    # this schema. Never run against real data without a verified backup.
    schema = memory_schema()
    for table in GUARDED_TABLES:
        op.execute(f'DROP TRIGGER IF EXISTS {table}_guard ON "{schema}".{table}')
    op.execute(f'DROP FUNCTION IF EXISTS "{schema}".me_guard_columns()')

    op.drop_index(
        op.f("ix_pm_provenance_owner_id_document_evidence_id"), "pm_provenance", schema=schema
    )
    op.drop_constraint(op.f("ck_pm_provenance_references_evidence"), "pm_provenance", schema=schema)
    op.create_check_constraint(
        op.f("ck_pm_provenance_references_evidence"),
        "pm_provenance",
        OLD_PROVENANCE_EVIDENCE,
        schema=schema,
    )
    op.drop_constraint(
        op.f("fk_pm_provenance_document_evidence_id_pm_document_evidence_ref"),
        "pm_provenance",
        schema=schema,
        type_="foreignkey",
    )
    op.drop_column("pm_provenance", "document_evidence_id", schema=schema)

    op.drop_table("pm_document_evidence_ref", schema=schema)
    op.drop_table("doc_processing_operation", schema=schema)
    op.drop_table("doc_embedding", schema=schema)
    op.drop_table("doc_chunk_location", schema=schema)
    op.drop_table("doc_chunk", schema=schema)
    op.drop_table("doc_extracted_representation", schema=schema)
    op.drop_constraint(
        op.f("fk_doc_document_current_version_id_doc_document_version"),
        "doc_document",
        schema=schema,
        type_="foreignkey",
    )
    op.drop_table("doc_document_version", schema=schema)
    op.drop_table("doc_document", schema=schema)
