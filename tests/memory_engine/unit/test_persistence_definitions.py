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

import pytest
from pydantic import SecretStr
from sqlalchemy import CheckConstraint
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import sessionmaker

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
    models,
)
from memory_engine.personal.application.ports import (
    AtomicMemoryRepository,
    CategoryRepository,
    DocumentEvidenceRepository,
    EntityMentionRepository,
    EntityRepository,
    EpisodeRepository,
    MemoryCandidateRepository,
    MemoryEmbeddingRepository,
    MemorySourceRepository,
    PersonalUnitOfWork,
    PersonalUnitOfWorkFactory,
    ProfileRepository,
    ProvenanceRepository,
    RelationshipRepository,
)

VERSIONS = Path(__file__).resolve().parents[3] / "memory-engine" / "migrations" / "versions"
MIGRATION = VERSIONS / "20261111_0001_personal_memory_core.py"
MIGRATION_0002 = VERSIONS / "20261111_0002_document_intelligence.py"
MIGRATION_0003 = VERSIONS / "20261111_0003_entities_and_relationships.py"
MIGRATION_0004 = VERSIONS / "20261111_0004_episodes_profiles_categories.py"
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
    "path", [MIGRATION_0002, MIGRATION_0003, MIGRATION_0004], ids=lambda p: p.stem[:13]
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
    assert len(VOCABULARIES) == 29


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
        "doc_document",
        "doc_document_version",
        "doc_extracted_representation",
        "doc_chunk",
        "doc_chunk_location",
        "doc_embedding",
        "doc_processing_operation",
    }
    for table in tables.values():
        assert table.c.owner_id.nullable is False


# Root tables have no owner-scoped parent; every other table must reach its parent
# through at least one foreign key that includes owner_id.
ROOT_TABLES = {"pm_memory_source", "pm_atomic_memory", "pm_entity", "pm_episode", "doc_document"}


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
