"""Persistence definitions that can be checked without a database.

* The migration's frozen vocabularies still equal the domain enums.
* The ORM models' check constraints are built from those same enums.
* Engine construction and error translation behave safely.
"""

import importlib.util
import re
from enum import StrEnum
from pathlib import Path
from types import ModuleType
from typing import cast

import pytest
from pydantic import SecretStr
from sqlalchemy import CheckConstraint
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session, sessionmaker

from memory_engine.config.settings import DatabaseSettings
from memory_engine.documents.application.ports import (
    DocumentContentRepository,
    DocumentRepository,
    DocumentUnitOfWork,
    DocumentUnitOfWorkFactory,
    ProcessingOperationRepository,
)
from memory_engine.documents.domain import vocabulary as doc_vocabulary
from memory_engine.domain import vocabulary
from memory_engine.exceptions import PersistenceError
from memory_engine.infrastructure.persistence import (
    SqlAlchemyDocumentUnitOfWorkFactory,
    SqlAlchemyPersonalUnitOfWorkFactory,
    build_database_url,
    create_database_engine,
    translate_database_errors,
)
from memory_engine.infrastructure.persistence.base import Base
from memory_engine.infrastructure.persistence.personal import (
    derived_models,
    entity_models,
    lifecycle_models,
    models,
)
from memory_engine.personal.application.ports import (
    AtomicMemoryRepository,
    CategoryRepository,
    CorrectionRepository,
    DeletionRepository,
    DocumentEvidenceRepository,
    EntityMentionRepository,
    EntityRepository,
    EpisodeRepository,
    EvaluationHistoryRepository,
    MemoryCandidateRepository,
    MemoryEmbeddingRepository,
    MemorySourceRepository,
    PersonalUnitOfWork,
    PersonalUnitOfWorkFactory,
    ProcessingHistoryRepository,
    ProfileRepository,
    ProvenanceRepository,
    RelationshipRepository,
)

VERSIONS = Path(__file__).resolve().parents[3] / "memory-engine" / "migrations" / "versions"
MIGRATION = VERSIONS / "20261111_0001_personal_memory_core.py"
MIGRATION_0002 = VERSIONS / "20261111_0002_document_intelligence.py"
MIGRATION_0003 = VERSIONS / "20261111_0003_entities_and_relationships.py"
MIGRATION_0004 = VERSIONS / "20261111_0004_episodes_profiles_categories.py"
MIGRATION_0005 = VERSIONS / "20261111_0005_processing_corrections_deletion.py"
MIGRATION_0006 = VERSIONS / "20261111_0006_episode_version.py"
MIGRATION_0007 = VERSIONS / "20261111_0007_memory_source_ingestion.py"
PASSWORD = "synthetic-db-password-91c2"  # noqa: S105 - test-only value


def _load_migration(path: Path = MIGRATION) -> ModuleType:
    spec = importlib.util.spec_from_file_location(f"migration_{path.stem}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("frozen_name", "enum"),
    [
        ("DOCUMENT_MEDIA_TYPES", doc_vocabulary.DocumentMediaType),
        ("DOCUMENT_LIFECYCLE_STATUSES", doc_vocabulary.DocumentLifecycleStatus),
        ("VERSION_PROCESSING_STATUSES", doc_vocabulary.VersionProcessingStatus),
        ("EXTRACTION_STATUSES", doc_vocabulary.ExtractionStatus),
        ("EMBEDDING_STATUSES", doc_vocabulary.EmbeddingStatus),
        ("OPERATION_TYPES", doc_vocabulary.OperationType),
        ("OPERATION_STATUSES", doc_vocabulary.OperationStatus),
        ("DOCUMENT_EVIDENCE_STATUSES", vocabulary.DocumentEvidenceStatus),
    ],
)
def test_migration_0002_vocabularies_match_domain_enums(
    frozen_name: str, enum: type[StrEnum]
) -> None:
    frozen = getattr(_load_migration(MIGRATION_0002), frozen_name)
    assert tuple(frozen) == tuple(member.value for member in enum)


def test_migration_0002_shares_the_evidence_rules_with_the_models() -> None:
    migration = _load_migration(MIGRATION_0002)
    assert migration.EVIDENCE_LINKS_MATCH_STATUS == models.EVIDENCE_LINKS_MATCH_STATUS
    assert migration.PROVENANCE_REFERENCES_EVIDENCE == models.PROVENANCE_REFERENCES_EVIDENCE
    assert migration.down_revision == _load_migration().revision


@pytest.mark.parametrize(
    "path",
    [MIGRATION_0002, MIGRATION_0003, MIGRATION_0004, MIGRATION_0005, MIGRATION_0006],
    ids=lambda p: p.stem[:13],
)
def test_every_guarded_column_list_names_real_columns(path: Path) -> None:
    for table, mutable in _load_migration(path).GUARDED_TABLES.items():
        columns = set(Base.metadata.tables[f"memory.{table}"].c.keys())
        assert set(mutable) <= columns, table
        assert "id" not in mutable and "owner_id" not in mutable, table


@pytest.mark.parametrize(
    ("frozen_name", "enum"),
    [
        ("ENTITY_SCOPES", vocabulary.EntityScope),
        ("ENTITY_TYPES", vocabulary.EntityType),
        ("ENTITY_STATUSES", vocabulary.EntityStatus),
        ("MENTION_RESOLUTION_STATUSES", vocabulary.MentionResolutionStatus),
        ("ENTITY_RESOLUTION_OUTCOMES", vocabulary.EntityResolutionOutcome),
        ("ENTITY_RELATIONSHIP_TYPES", vocabulary.EntityRelationshipType),
        ("MEMORY_RELATIONSHIP_TYPES", vocabulary.MemoryRelationshipType),
        ("SUPERSESSION_REASONS", vocabulary.SupersessionReason),
        ("MEMORY_ENTITY_ROLES", vocabulary.MemoryEntityRole),
        ("PROVENANCE_ORIGIN_KINDS", vocabulary.ProvenanceOriginKind),
    ],
)
def test_migration_0003_vocabularies_match_domain_enums(
    frozen_name: str, enum: type[StrEnum]
) -> None:
    frozen = getattr(_load_migration(MIGRATION_0003), frozen_name)
    assert tuple(frozen) == tuple(member.value for member in enum)


@pytest.mark.parametrize(
    "rule",
    [
        "MENTION_OUTCOMES",
        "ASSIGNING_OUTCOMES",
        "CHANGING_OUTCOMES",
        "SYMMETRIC_ENTITY_TYPES",
        "SYMMETRIC_MEMORY_TYPES",
        "PREVIOUS_DIFFERS",
    ],
)
def test_migration_0003_rules_match_the_models(rule: str) -> None:
    migration = _load_migration(MIGRATION_0003)
    assert getattr(migration, rule) == getattr(entity_models, rule)
    assert migration.down_revision == _load_migration(MIGRATION_0002).revision


@pytest.mark.parametrize(
    ("frozen_name", "enum"),
    [
        ("SOURCE_TYPES", vocabulary.SourceType),
        ("SOURCE_PROCESSING_STATUSES", vocabulary.SourceProcessingStatus),
        ("CANDIDATE_STATUSES", vocabulary.CandidateStatus),
        ("CANDIDATE_ORIGINS", vocabulary.CandidateOrigin),
        ("MEMORY_ORIGINS", vocabulary.MemoryOrigin),
        ("MEMORY_LIFECYCLE_STATUSES", vocabulary.MemoryLifecycleStatus),
        ("REVISION_CHANGE_TYPES", vocabulary.RevisionChangeType),
        ("PROVENANCE_ROLES", vocabulary.ProvenanceRole),
        ("PROVENANCE_ORIGIN_KINDS", vocabulary.ProvenanceOriginKind),
    ],
)
def test_migration_vocabularies_match_domain_enums(frozen_name: str, enum: type[StrEnum]) -> None:
    frozen = getattr(_load_migration(), frozen_name)
    assert tuple(frozen) == tuple(member.value for member in enum)


def test_migration_and_models_share_the_content_lifecycle_rule() -> None:
    assert _load_migration().CONTENT_MATCHES_LIFECYCLE == models.CONTENT_MATCHES_LIFECYCLE


VOCABULARIES = [
    value
    for value in vars(vocabulary).values()
    if isinstance(value, type) and issubclass(value, StrEnum) and value is not StrEnum
]


def test_vocabulary_module_defines_the_expected_enums() -> None:
    assert len(VOCABULARIES) == 39


def test_documents_reuse_the_shared_embedding_status() -> None:
    assert doc_vocabulary.EmbeddingStatus is vocabulary.EmbeddingStatus


@pytest.mark.parametrize(
    ("frozen_name", "enum"),
    [
        ("EPISODE_STATUSES", vocabulary.EpisodeStatus),
        ("TEMPORAL_PRECISIONS", vocabulary.TemporalPrecision),
        ("PROFILE_TYPES", vocabulary.ProfileType),
        ("PROFILE_STATUSES", vocabulary.ProfileStatus),
        ("REFRESH_TRIGGERS", vocabulary.RefreshTrigger),
        ("REFRESH_OUTCOMES", vocabulary.RefreshOutcome),
        ("MEMORY_CATEGORIES", vocabulary.MemoryCategory),
        ("MEMORY_ORIGINS", vocabulary.MemoryOrigin),
        ("EMBEDDING_PURPOSES", vocabulary.EmbeddingPurpose),
        ("EMBEDDING_STATUSES", vocabulary.EmbeddingStatus),
    ],
)
def test_migration_0004_vocabularies_match_domain_enums(
    frozen_name: str, enum: type[StrEnum]
) -> None:
    frozen = getattr(_load_migration(MIGRATION_0004), frozen_name)
    assert tuple(frozen) == tuple(member.value for member in enum)


def test_migration_0004_rules_match_the_models() -> None:
    migration = _load_migration(MIGRATION_0004)
    assert migration.REVISION_OUTCOMES == derived_models.REVISION_OUTCOMES
    assert migration.SAFE_ERROR_CODE == derived_models.SAFE_ERROR_CODE
    assert migration.down_revision == _load_migration(MIGRATION_0003).revision


@pytest.mark.parametrize(
    ("frozen_name", "enum"),
    [
        ("SOURCE_PROCESSING_STATUSES", vocabulary.SourceProcessingStatus),
        ("CANDIDATE_STATUSES", vocabulary.CandidateStatus),
        ("PROCESSING_EVENT_TYPES", vocabulary.ProcessingEventType),
        ("EVALUATION_OUTCOMES", vocabulary.EvaluationOutcome),
        ("CORRECTION_STATUSES", vocabulary.CorrectionStatus),
        ("DELETION_REQUEST_KINDS", vocabulary.DeletionRequestKind),
        ("DELETION_OPERATION_STATUSES", vocabulary.DeletionOperationStatus),
        ("DELETION_TARGET_KINDS", vocabulary.DeletionTargetKind),
        ("DELETION_ACTIONS", vocabulary.DeletionAction),
        ("DELETION_TARGET_STATES", vocabulary.DeletionTargetState),
    ],
)
def test_migration_0005_vocabularies_match_domain_enums(
    frozen_name: str, enum: type[StrEnum]
) -> None:
    frozen = getattr(_load_migration(MIGRATION_0005), frozen_name)
    assert tuple(frozen) == tuple(member.value for member in enum)


@pytest.mark.parametrize("rule", ["OUTCOME_STATUSES", "RESOLVED_CORRECTION", "FINISHED_DELETION"])
def test_migration_0005_rules_match_the_models(rule: str) -> None:
    migration = _load_migration(MIGRATION_0005)
    assert getattr(migration, rule) == getattr(lifecycle_models, rule)
    assert migration.down_revision == _load_migration(MIGRATION_0004).revision


def test_migration_0007_matches_the_models_and_enums() -> None:
    migration = _load_migration(MIGRATION_0007)
    assert tuple(t.value for t in vocabulary.InstructionType) == migration.INSTRUCTION_TYPES
    assert tuple(p.value for p in vocabulary.IngestionPriority) == migration.INGESTION_PRIORITIES
    assert migration.IDEMPOTENCY_PAIR == models.IDEMPOTENCY_PAIR
    assert migration.INSTRUCTION_PRIORITY == models.INSTRUCTION_PRIORITY
    assert migration.down_revision == _load_migration(MIGRATION_0006).revision
    columns = set(Base.metadata.tables["memory.pm_memory_source"].c.keys())
    assert {"instruction_type", "priority", "idempotency_key", "normalized_ref"} <= columns


def test_migration_0006_extends_the_episode_guard_from_0004() -> None:
    migration = _load_migration(MIGRATION_0006)
    before = _load_migration(MIGRATION_0004).GUARDED_TABLES["pm_episode"]
    assert before == migration.EPISODE_MUTABLE_0004
    assert migration.GUARDED_TABLES["pm_episode"] == (*before, "version")
    assert migration.down_revision == _load_migration(MIGRATION_0005).revision


def test_the_deletion_ledger_can_name_every_personal_memory_table() -> None:
    # Deletion must reach every derived record (6.5.9): one target kind per pm_ table,
    # except the deletion records themselves.
    pm_tables = {
        t.name.removeprefix("pm_")
        for t in Base.metadata.tables.values()
        if t.name.startswith("pm_") and not t.name.startswith("pm_deletion_")
    }
    assert {kind.value for kind in vocabulary.DeletionTargetKind} == pm_tables


def test_sqlalchemy_adapters_satisfy_the_application_ports() -> None:
    # Checked statically by mypy (structural typing) and at runtime by construction.
    session_factory = sessionmaker()
    factory: PersonalUnitOfWorkFactory = SqlAlchemyPersonalUnitOfWorkFactory(session_factory)
    unit: PersonalUnitOfWork = factory().__enter__()
    sources: MemorySourceRepository = unit.sources
    candidates: MemoryCandidateRepository = unit.candidates
    memories: AtomicMemoryRepository = unit.memories
    provenance: ProvenanceRepository = unit.provenance
    assert all(port is not None for port in (sources, candidates, memories, provenance))
    evidence: DocumentEvidenceRepository = unit.evidence
    entities: EntityRepository = unit.entities
    mentions: EntityMentionRepository = unit.mentions
    relationships: RelationshipRepository = unit.relationships
    assert all(port is not None for port in (evidence, entities, mentions, relationships))
    episodes: EpisodeRepository = unit.episodes
    profiles: ProfileRepository = unit.profiles
    categories: CategoryRepository = unit.categories
    memory_embeddings: MemoryEmbeddingRepository = unit.memory_embeddings
    assert all(port is not None for port in (episodes, profiles, categories, memory_embeddings))
    processing: ProcessingHistoryRepository = unit.processing
    evaluations: EvaluationHistoryRepository = unit.evaluations
    corrections: CorrectionRepository = unit.corrections
    deletions: DeletionRepository = unit.deletions
    assert all(port is not None for port in (processing, evaluations, corrections, deletions))
    doc_factory: DocumentUnitOfWorkFactory = SqlAlchemyDocumentUnitOfWorkFactory(session_factory)
    doc_unit: DocumentUnitOfWork = doc_factory().__enter__()
    documents: DocumentRepository = doc_unit.documents
    contents: DocumentContentRepository = doc_unit.contents
    operations: ProcessingOperationRepository = doc_unit.operations
    assert all(port is not None for port in (documents, contents, operations))
    concrete = SqlAlchemyPersonalUnitOfWorkFactory(session_factory)()
    concrete.__enter__()
    with pytest.raises(RuntimeError, match="already active"):
        concrete.__enter__()
    concrete.__exit__(None, None, None)


@pytest.mark.parametrize("enum", VOCABULARIES, ids=lambda enum: enum.__name__)
def test_vocabulary_values_are_lowercase_snake_case(enum: type[StrEnum]) -> None:
    assert all(re.fullmatch(r"[a-z][a-z0-9_]*", member.value) for member in enum)


def test_every_table_is_owner_scoped_with_a_domain_prefix() -> None:
    tables = {t.name: t for t in Base.metadata.tables.values() if t.schema == "memory"}
    assert set(tables) == {
        "pm_memory_source",
        "pm_memory_candidate",
        "pm_atomic_memory",
        "pm_atomic_memory_revision",
        "pm_provenance",
        "pm_document_evidence_ref",
        "pm_entity",
        "pm_entity_alias",
        "pm_entity_mention",
        "pm_entity_resolution",
        "pm_entity_relationship",
        "pm_memory_relationship",
        "pm_memory_entity",
        "pm_episode",
        "pm_episode_membership",
        "pm_episode_event",
        "pm_profile",
        "pm_profile_revision",
        "pm_profile_memory",
        "pm_profile_refresh",
        "pm_memory_category",
        "pm_memory_embedding",
        "pm_source_processing_event",
        "pm_candidate_evaluation",
        "pm_correction_request",
        "pm_correction_memory",
        "pm_deletion_operation",
        "pm_deletion_target",
        "doc_document",
        "doc_document_version",
        "doc_extracted_representation",
        "doc_chunk",
        "doc_chunk_location",
        "doc_embedding",
        "doc_processing_operation",
        "me_outbox",
    }
    for table in tables.values():
        assert table.c.owner_id.nullable is False


# Root tables have no owner-scoped parent; every other table must reach its parent
# through at least one foreign key that includes owner_id.
ROOT_TABLES = {
    "pm_memory_source",
    "pm_atomic_memory",
    "pm_entity",
    "pm_episode",
    "pm_correction_request",
    "pm_deletion_operation",
    "doc_document",
    # The outbox has no foreign key to its subject, which lives in either domain
    # (only the evidence path may cross them); see infrastructure/persistence/outbox.py.
    "me_outbox",
}


def test_foreign_keys_never_cascade_and_every_child_has_an_owner_key() -> None:
    for table in Base.metadata.tables.values():
        for fk in table.foreign_key_constraints:
            assert fk.ondelete == "RESTRICT", fk.name
        if table.name not in ROOT_TABLES:
            assert any("owner_id" in fk.column_keys for fk in table.foreign_key_constraints), (
                table.name
            )


def test_only_the_evidence_path_crosses_domains() -> None:
    # Personal Memory may reference documents only through pm_document_evidence_ref;
    # Document Intelligence never references Personal Memory.
    for table in Base.metadata.tables.values():
        for fk in table.foreign_key_constraints:
            referred = fk.referred_table.name
            if table.name.startswith("doc_"):
                assert referred.startswith("doc_"), fk.name
            elif referred.startswith("doc_"):
                assert table.name == "pm_document_evidence_ref", fk.name


def test_model_check_constraints_list_every_enum_value() -> None:
    lifecycle = next(
        c
        for c in Base.metadata.tables["memory.pm_atomic_memory"].constraints
        if isinstance(c, CheckConstraint) and c.name == "ck_pm_atomic_memory_lifecycle_status"
    )
    for status in vocabulary.MemoryLifecycleStatus:
        assert f"'{status.value}'" in str(lifecycle.sqltext)


def test_constraint_names_fit_postgresql_identifier_limit() -> None:
    for table in Base.metadata.tables.values():
        names = [c.name for c in table.constraints] + [i.name for i in table.indexes]
        for name in names:
            assert isinstance(name, str)
            assert len(name) <= 63, name


# --- engine and error translation -------------------------------------------------


def _settings(**overrides: object) -> DatabaseSettings:
    values: dict[str, object] = {
        "host": "db.test.invalid",
        "name": "raven_test",
        "user": "raven_memory_role",
        "password": SecretStr(PASSWORD),
    }
    return DatabaseSettings.model_validate({**values, **overrides})


def test_database_url_masks_the_password() -> None:
    url = build_database_url(_settings())
    assert url.drivername == "postgresql+psycopg"
    assert PASSWORD not in str(url)
    assert PASSWORD not in repr(url)
    assert url.password == PASSWORD


def test_engine_uses_safe_defaults_without_connecting() -> None:
    engine = create_database_engine(_settings(pool_size=3, max_overflow=1))
    try:
        assert engine.hide_parameters is True
        assert engine.pool.size() == 3  # type: ignore[attr-defined]
        assert "schema_translate_map" not in engine.get_execution_options()
    finally:
        engine.dispose()


def test_engine_maps_a_custom_schema_name() -> None:
    engine = create_database_engine(_settings(schema_name="memory_tenant_x"))
    try:
        assert engine.get_execution_options()["schema_translate_map"] == {
            "memory": "memory_tenant_x"
        }
    finally:
        engine.dispose()


class _Diag:
    constraint_name = "uq_example"


class _DriverError(Exception):
    diag = _Diag()


def test_integrity_errors_become_persistence_errors_with_constraint_name() -> None:
    with pytest.raises(PersistenceError) as caught, translate_database_errors("add example"):
        raise IntegrityError("INSERT ...", {"content": "private text"}, _DriverError())
    assert caught.value.details == {"constraint": "uq_example"}
    assert "private text" not in str(caught.value)
    assert isinstance(caught.value.__cause__, IntegrityError)


def test_connection_errors_become_persistence_errors() -> None:
    with (
        pytest.raises(PersistenceError, match="Database operation failed: get example"),
        translate_database_errors("get example"),
    ):
        raise OperationalError("SELECT 1", None, Exception("connection refused"))


def test_domain_errors_pass_through_untranslated() -> None:
    with pytest.raises(ValueError, match="kept"), translate_database_errors("noop"):
        raise ValueError("kept")


class _FailingCommitSession:
    """Stands in for a Session whose COMMIT fails (for example, the connection drops)."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def commit(self) -> None:
        self.calls.append("commit")
        raise OperationalError("COMMIT", None, Exception("server closed the connection"))

    def rollback(self) -> None:
        self.calls.append("rollback")

    def close(self) -> None:
        self.calls.append("close")


def test_a_failed_commit_is_reported_rolled_back_and_closed() -> None:
    # Plan 8.2 section 13 "database write failure": never report success before commit.
    session = _FailingCommitSession()
    factory = SqlAlchemyPersonalUnitOfWorkFactory(cast("sessionmaker[Session]", lambda: session))
    completed = False
    with pytest.raises(PersistenceError, match="commit unit of work"):
        with factory():
            pass
        completed = True
    assert not completed
    assert session.calls == ["commit", "rollback", "close"]
