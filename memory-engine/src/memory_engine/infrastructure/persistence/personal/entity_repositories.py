"""SQLAlchemy implementations of the entity, mention and relationship ports.

Same contract as the other Personal Memory repositories: owner-scoped SQL,
scope checks before writes, domain records out, conditional updates for state
changes. Alias and name matching only *finds candidates*; identity decisions
are recorded as resolution history and never inferred from similarity
(Decisions 5.4.12, 5.4.14).
"""

import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import ColumnElement, exists, or_, select, update
from sqlalchemy.orm import Session

from memory_engine.domain.errors import DomainValidationError, OwnershipError
from memory_engine.domain.identifiers import OwnerScope
from memory_engine.domain.vocabulary import (
    EntityRelationshipType,
    EntityResolutionOutcome,
    EntityScope,
    EntityStatus,
    EntityType,
    MemoryEntityRole,
    MemoryLifecycleStatus,
    MemoryRelationshipType,
    MentionResolutionStatus,
    ProvenanceOriginKind,
    SupersessionReason,
)
from memory_engine.exceptions import RecordNotFoundError
from memory_engine.infrastructure.persistence.database import (
    conditional_update,
    translate_database_errors,
)
from memory_engine.infrastructure.persistence.personal.entity_models import (
    EntityAliasRow,
    EntityMentionRow,
    EntityRelationshipRow,
    EntityResolutionRow,
    EntityRow,
    MemoryEntityRow,
    MemoryRelationshipRow,
)
from memory_engine.infrastructure.persistence.personal.models import (
    AtomicMemoryRow,
    MemoryCandidateRow,
    MemorySourceRow,
)
from memory_engine.personal.domain import (
    Entity,
    EntityAlias,
    EntityMention,
    EntityRelationship,
    EntityResolutionRecord,
    MemoryEntityAssociation,
    MemoryRelationship,
)

MAX_MERGE_CHAIN = 32
_TOMBSTONED_MEMORY = (
    MemoryLifecycleStatus.DELETION_PENDING.value,
    MemoryLifecycleStatus.DELETED.value,
)


def _require_in_scope(scope: OwnerScope, *owner_ids: uuid.UUID) -> None:
    if not all(scope.owns(owner_id) for owner_id in owner_ids):
        raise OwnershipError("record owner does not match the operation's owner scope")


def _row_exists(
    session: Session,
    model: type[MemorySourceRow] | type[MemoryCandidateRow],
    scope: OwnerScope,
    row_id: uuid.UUID,
) -> bool:
    return bool(
        session.scalar(select(exists().where(model.id == row_id, model.owner_id == scope.owner_id)))
    )


def _entity_status(session: Session, scope: OwnerScope, entity_id: uuid.UUID) -> str | None:
    status = session.scalar(
        select(EntityRow.status).where(
            EntityRow.id == entity_id, EntityRow.owner_id == scope.owner_id
        )
    )
    return None if status in (None, EntityStatus.DELETED.value) else status


def _require_active_entity(session: Session, scope: OwnerScope, entity_id: uuid.UUID) -> None:
    status = _entity_status(session, scope, entity_id)
    if status is None:
        raise RecordNotFoundError("entity not found")
    if status != EntityStatus.ACTIVE.value:
        raise DomainValidationError("only an active entity can take new references")


def _require_live_memory(session: Session, scope: OwnerScope, memory_id: uuid.UUID) -> None:
    if not session.scalar(
        select(
            exists().where(
                AtomicMemoryRow.id == memory_id,
                AtomicMemoryRow.owner_id == scope.owner_id,
                AtomicMemoryRow.lifecycle_status.not_in(_TOMBSTONED_MEMORY),
            )
        )
    ):
        raise RecordNotFoundError("atomic memory not found")


# --- mapping -----------------------------------------------------------------------


def _entity(row: EntityRow) -> Entity:
    return Entity(
        id=row.id,
        owner_id=row.owner_id,
        entity_type=EntityType(row.entity_type),
        canonical_name=row.canonical_name,
        status=EntityStatus(row.status),
        scope=EntityScope(row.scope),
        merged_into_id=row.merged_into_id,
    )


def _mention(row: EntityMentionRow) -> EntityMention:
    return EntityMention(
        id=row.id,
        owner_id=row.owner_id,
        source_id=row.source_id,
        mention_text=row.mention_text,
        mention_type=EntityType(row.mention_type),
        resolution_status=MentionResolutionStatus(row.resolution_status),
        entity_id=row.entity_id,
        candidate_id=row.candidate_id,
        confidence=row.confidence,
        start_offset=row.start_offset,
        end_offset=row.end_offset,
        context=row.context,
    )


def _resolution(row: EntityResolutionRow) -> EntityResolutionRecord:
    return EntityResolutionRecord(
        id=row.id,
        owner_id=row.owner_id,
        outcome=EntityResolutionOutcome(row.outcome),
        recorded_at=row.recorded_at,
        mention_id=row.mention_id,
        entity_id=row.entity_id,
        previous_entity_id=row.previous_entity_id,
        candidate_entity_ids=tuple(uuid.UUID(value) for value in row.candidate_entity_ids),
        rationale=row.rationale,
        evidence=row.evidence,
    )


def _resolution_row(record: EntityResolutionRecord) -> EntityResolutionRow:
    return EntityResolutionRow(
        id=record.id,
        owner_id=record.owner_id,
        outcome=record.outcome.value,
        mention_id=record.mention_id,
        entity_id=record.entity_id,
        previous_entity_id=record.previous_entity_id,
        candidate_entity_ids=[str(value) for value in record.candidate_entity_ids],
        rationale=record.rationale,
        evidence=dict(record.evidence),
        recorded_at=record.recorded_at,
    )


def _entity_relationship(row: EntityRelationshipRow) -> EntityRelationship:
    return EntityRelationship(
        id=row.id,
        owner_id=row.owner_id,
        source_entity_id=row.source_entity_id,
        target_entity_id=row.target_entity_id,
        relationship_type=EntityRelationshipType(row.relationship_type),
        origin_kind=ProvenanceOriginKind(row.origin_kind),
        recorded_at=row.recorded_at,
        valid_from=row.valid_from,
        valid_to=row.valid_to,
        superseded_at=row.superseded_at,
        confidence=row.confidence,
        source_id=row.source_id,
    )


def _memory_relationship(row: MemoryRelationshipRow) -> MemoryRelationship:
    return MemoryRelationship(
        id=row.id,
        owner_id=row.owner_id,
        source_memory_id=row.source_memory_id,
        target_memory_id=row.target_memory_id,
        relationship_type=MemoryRelationshipType(row.relationship_type),
        origin_kind=ProvenanceOriginKind(row.origin_kind),
        recorded_at=row.recorded_at,
        reason=None if row.reason is None else SupersessionReason(row.reason),
        valid_from=row.valid_from,
        valid_to=row.valid_to,
        superseded_at=row.superseded_at,
        confidence=row.confidence,
    )


def _association(row: MemoryEntityRow) -> MemoryEntityAssociation:
    return MemoryEntityAssociation(
        id=row.id,
        owner_id=row.owner_id,
        memory_id=row.memory_id,
        entity_id=row.entity_id,
        role=MemoryEntityRole(row.role),
    )


# --- entities and aliases ----------------------------------------------------------


class SqlAlchemyEntityRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, scope: OwnerScope, entity: Entity) -> None:
        _require_in_scope(scope, entity.owner_id)
        if entity.status is not EntityStatus.ACTIVE:
            raise DomainValidationError("a new entity starts active")
        with translate_database_errors("add entity"):
            self._session.add(
                EntityRow(
                    id=entity.id,
                    owner_id=entity.owner_id,
                    scope=entity.scope.value,
                    entity_type=entity.entity_type.value,
                    canonical_name=entity.canonical_name,
                    normalized_name=EntityAlias.normalize(entity.canonical_name),
                    status=entity.status.value,
                    merged_into_id=None,
                )
            )
            self._session.flush()

    def get(self, scope: OwnerScope, entity_id: uuid.UUID) -> Entity | None:
        with translate_database_errors("get entity"):
            row = self._session.scalar(
                select(EntityRow)
                .where(
                    EntityRow.id == entity_id,
                    EntityRow.owner_id == scope.owner_id,
                    EntityRow.status != EntityStatus.DELETED.value,
                )
                .execution_options(populate_existing=True)
            )
        return None if row is None else _entity(row)

    def canonical(self, scope: OwnerScope, entity_id: uuid.UUID) -> Entity | None:
        current = self.get(scope, entity_id)
        for _ in range(MAX_MERGE_CHAIN):
            if current is None or current.merged_into_id is None:
                return current
            current = self.get(scope, current.merged_into_id)
        raise DomainValidationError("merge chain too long or cyclic")

    def add_alias(self, scope: OwnerScope, alias: EntityAlias) -> None:
        _require_in_scope(scope, alias.owner_id)
        with translate_database_errors("add entity alias"):
            _require_active_entity(self._session, scope, alias.entity_id)
            if alias.source_id is not None and not _row_exists(
                self._session, MemorySourceRow, scope, alias.source_id
            ):
                raise RecordNotFoundError("memory source not found")
            self._session.add(
                EntityAliasRow(
                    id=alias.id,
                    owner_id=alias.owner_id,
                    entity_id=alias.entity_id,
                    alias=alias.alias,
                    normalized_alias=EntityAlias.normalize(alias.alias),
                    source_id=alias.source_id,
                )
            )
            self._session.flush()

    def list_aliases(self, scope: OwnerScope, entity_id: uuid.UUID) -> Sequence[EntityAlias]:
        with translate_database_errors("list entity aliases"):
            rows = self._session.scalars(
                select(EntityAliasRow)
                .where(
                    EntityAliasRow.owner_id == scope.owner_id,
                    EntityAliasRow.entity_id == entity_id,
                )
                .order_by(EntityAliasRow.created_at, EntityAliasRow.id)
            ).all()
        return [
            EntityAlias(
                id=row.id,
                owner_id=row.owner_id,
                entity_id=row.entity_id,
                alias=row.alias,
                source_id=row.source_id,
            )
            for row in rows
        ]

    def find_by_alias(self, scope: OwnerScope, text: str) -> Sequence[Entity]:
        key = EntityAlias.normalize(text)
        if not key:
            return []
        with translate_database_errors("find entities by alias"):
            alias_match = select(EntityAliasRow.entity_id).where(
                EntityAliasRow.owner_id == scope.owner_id,
                EntityAliasRow.normalized_alias == key,
            )
            rows = self._session.scalars(
                select(EntityRow)
                .where(
                    EntityRow.owner_id == scope.owner_id,
                    EntityRow.status == EntityStatus.ACTIVE.value,
                    or_(EntityRow.normalized_name == key, EntityRow.id.in_(alias_match)),
                )
                .order_by(EntityRow.id)
                .execution_options(populate_existing=True)
            ).all()
        return [_entity(row) for row in rows]

    def merge(self, scope: OwnerScope, record: EntityResolutionRecord) -> None:
        _require_in_scope(scope, record.owner_id)
        if record.outcome is not EntityResolutionOutcome.MERGED:
            raise DomainValidationError("merge needs a 'merged' resolution record")
        merged_id, survivor_id = record.previous_entity_id, record.entity_id
        if merged_id is None or survivor_id is None:  # pragma: no cover - record invariant
            raise DomainValidationError("a merge names both entities")
        with translate_database_errors("merge entities"):
            _require_active_entity(self._session, scope, survivor_id)
            conditional_update(
                self._session,
                update(EntityRow)
                .where(
                    EntityRow.id == merged_id,
                    EntityRow.owner_id == scope.owner_id,
                    EntityRow.status == EntityStatus.ACTIVE.value,
                )
                .values(status=EntityStatus.MERGED.value, merged_into_id=survivor_id),
                exists=select(EntityRow.id)
                .where(
                    EntityRow.id == merged_id,
                    EntityRow.owner_id == scope.owner_id,
                    EntityRow.status != EntityStatus.DELETED.value,
                )
                .exists(),
                what="entity",
            )
            self._session.add(_resolution_row(record))
            self._session.flush()


# --- mentions and resolution history -----------------------------------------------


class SqlAlchemyEntityMentionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, scope: OwnerScope, mention: EntityMention) -> None:
        _require_in_scope(scope, mention.owner_id)
        with translate_database_errors("add entity mention"):
            if not _row_exists(self._session, MemorySourceRow, scope, mention.source_id):
                raise RecordNotFoundError("memory source not found")
            if mention.candidate_id is not None and not _row_exists(
                self._session, MemoryCandidateRow, scope, mention.candidate_id
            ):
                raise RecordNotFoundError("memory candidate not found")
            if mention.entity_id is not None:
                _require_active_entity(self._session, scope, mention.entity_id)
            self._session.add(
                EntityMentionRow(
                    id=mention.id,
                    owner_id=mention.owner_id,
                    source_id=mention.source_id,
                    candidate_id=mention.candidate_id,
                    mention_text=mention.mention_text,
                    mention_type=mention.mention_type.value,
                    resolution_status=mention.resolution_status.value,
                    entity_id=mention.entity_id,
                    confidence=mention.confidence,
                    start_offset=mention.start_offset,
                    end_offset=mention.end_offset,
                    context=dict(mention.context),
                )
            )
            self._session.flush()

    def get(self, scope: OwnerScope, mention_id: uuid.UUID) -> EntityMention | None:
        with translate_database_errors("get entity mention"):
            row = self._session.scalar(
                select(EntityMentionRow)
                .where(
                    EntityMentionRow.id == mention_id,
                    EntityMentionRow.owner_id == scope.owner_id,
                )
                .execution_options(populate_existing=True)
            )
        return None if row is None else _mention(row)

    def list_for_entity(self, scope: OwnerScope, entity_id: uuid.UUID) -> Sequence[EntityMention]:
        with translate_database_errors("list entity mentions"):
            rows = self._session.scalars(
                select(EntityMentionRow)
                .where(
                    EntityMentionRow.owner_id == scope.owner_id,
                    EntityMentionRow.entity_id == entity_id,
                )
                .order_by(EntityMentionRow.created_at, EntityMentionRow.id)
                .execution_options(populate_existing=True)
            ).all()
        return [_mention(row) for row in rows]

    def apply_resolution(
        self,
        scope: OwnerScope,
        record: EntityResolutionRecord,
        *,
        expected_status: MentionResolutionStatus,
    ) -> EntityMention:
        _require_in_scope(scope, record.owner_id)
        if record.mention_id is None:
            raise DomainValidationError("a mention resolution names its mention")
        new_status = record.mention_status()
        with translate_database_errors("apply entity resolution"):
            if record.entity_id is not None:
                _require_active_entity(self._session, scope, record.entity_id)
            guard = [
                EntityMentionRow.id == record.mention_id,
                EntityMentionRow.owner_id == scope.owner_id,
                EntityMentionRow.resolution_status == expected_status.value,
            ]
            if record.previous_entity_id is not None:
                # A correction or reassignment must replace the entity it names.
                guard.append(EntityMentionRow.entity_id == record.previous_entity_id)
            conditional_update(
                self._session,
                update(EntityMentionRow)
                .where(*guard)
                .values(resolution_status=new_status.value, entity_id=record.entity_id),
                exists=select(EntityMentionRow.id)
                .where(
                    EntityMentionRow.id == record.mention_id,
                    EntityMentionRow.owner_id == scope.owner_id,
                )
                .exists(),
                what="entity mention",
            )
            self._session.add(_resolution_row(record))
            self._session.flush()
        updated = self.get(scope, record.mention_id)
        if updated is None:  # pragma: no cover - updated in this transaction
            raise RecordNotFoundError("entity mention not found")
        return updated

    def history(
        self,
        scope: OwnerScope,
        *,
        mention_id: uuid.UUID | None = None,
        entity_id: uuid.UUID | None = None,
    ) -> Sequence[EntityResolutionRecord]:
        if (mention_id is None) == (entity_id is None):
            raise DomainValidationError("give exactly one of mention_id or entity_id")
        condition = (
            EntityResolutionRow.mention_id == mention_id
            if mention_id is not None
            else or_(
                EntityResolutionRow.entity_id == entity_id,
                EntityResolutionRow.previous_entity_id == entity_id,
            )
        )
        with translate_database_errors("list entity resolution history"):
            rows = self._session.scalars(
                select(EntityResolutionRow)
                .where(EntityResolutionRow.owner_id == scope.owner_id, condition)
                .order_by(EntityResolutionRow.recorded_at, EntityResolutionRow.seq)
            ).all()
        return [_resolution(row) for row in rows]


# --- relationships and memory-entity associations ----------------------------------


class SqlAlchemyRelationshipRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add_entity_relationship(self, scope: OwnerScope, relationship: EntityRelationship) -> None:
        _require_in_scope(scope, relationship.owner_id)
        if relationship.superseded_at is not None:
            raise DomainValidationError("a new relationship is current")
        with translate_database_errors("add entity relationship"):
            _require_active_entity(self._session, scope, relationship.source_entity_id)
            _require_active_entity(self._session, scope, relationship.target_entity_id)
            if relationship.source_id is not None and not _row_exists(
                self._session, MemorySourceRow, scope, relationship.source_id
            ):
                raise RecordNotFoundError("memory source not found")
            self._session.add(
                EntityRelationshipRow(
                    id=relationship.id,
                    owner_id=relationship.owner_id,
                    source_entity_id=relationship.source_entity_id,
                    target_entity_id=relationship.target_entity_id,
                    relationship_type=relationship.relationship_type.value,
                    origin_kind=relationship.origin_kind.value,
                    confidence=relationship.confidence,
                    valid_from=relationship.valid_from,
                    valid_to=relationship.valid_to,
                    recorded_at=relationship.recorded_at,
                    source_id=relationship.source_id,
                )
            )
            self._session.flush()

    def close_entity_relationship(
        self,
        scope: OwnerScope,
        relationship_id: uuid.UUID,
        *,
        valid_to: datetime | None,
        superseded_at: datetime,
    ) -> None:
        self._close(EntityRelationshipRow, scope, relationship_id, valid_to, superseded_at)

    def entity_relationships(
        self, scope: OwnerScope, entity_id: uuid.UUID, *, include_history: bool = False
    ) -> Sequence[EntityRelationship]:
        statement = select(EntityRelationshipRow).where(
            EntityRelationshipRow.owner_id == scope.owner_id,
            or_(
                EntityRelationshipRow.source_entity_id == entity_id,
                EntityRelationshipRow.target_entity_id == entity_id,
            ),
        )
        if not include_history:
            statement = statement.where(EntityRelationshipRow.superseded_at.is_(None))
        with translate_database_errors("list entity relationships"):
            rows = self._session.scalars(
                statement.order_by(
                    EntityRelationshipRow.recorded_at, EntityRelationshipRow.id
                ).execution_options(populate_existing=True)
            ).all()
        return [_entity_relationship(row) for row in rows]

    def add_memory_relationship(self, scope: OwnerScope, relationship: MemoryRelationship) -> None:
        _require_in_scope(scope, relationship.owner_id)
        if relationship.superseded_at is not None:
            raise DomainValidationError("a new relationship is current")
        with translate_database_errors("add memory relationship"):
            _require_live_memory(self._session, scope, relationship.source_memory_id)
            _require_live_memory(self._session, scope, relationship.target_memory_id)
            self._session.add(
                MemoryRelationshipRow(
                    id=relationship.id,
                    owner_id=relationship.owner_id,
                    source_memory_id=relationship.source_memory_id,
                    target_memory_id=relationship.target_memory_id,
                    relationship_type=relationship.relationship_type.value,
                    reason=None if relationship.reason is None else relationship.reason.value,
                    origin_kind=relationship.origin_kind.value,
                    confidence=relationship.confidence,
                    valid_from=relationship.valid_from,
                    valid_to=relationship.valid_to,
                    recorded_at=relationship.recorded_at,
                )
            )
            self._session.flush()

    def close_memory_relationship(
        self,
        scope: OwnerScope,
        relationship_id: uuid.UUID,
        *,
        valid_to: datetime | None,
        superseded_at: datetime,
    ) -> None:
        self._close(MemoryRelationshipRow, scope, relationship_id, valid_to, superseded_at)

    def memory_relationships(
        self, scope: OwnerScope, memory_id: uuid.UUID, *, include_history: bool = False
    ) -> Sequence[MemoryRelationship]:
        statement = select(MemoryRelationshipRow).where(
            MemoryRelationshipRow.owner_id == scope.owner_id,
            or_(
                MemoryRelationshipRow.source_memory_id == memory_id,
                MemoryRelationshipRow.target_memory_id == memory_id,
            ),
        )
        if not include_history:
            statement = statement.where(MemoryRelationshipRow.superseded_at.is_(None))
        with translate_database_errors("list memory relationships"):
            rows = self._session.scalars(
                statement.order_by(
                    MemoryRelationshipRow.recorded_at, MemoryRelationshipRow.id
                ).execution_options(populate_existing=True)
            ).all()
        return [_memory_relationship(row) for row in rows]

    def associate(self, scope: OwnerScope, association: MemoryEntityAssociation) -> None:
        _require_in_scope(scope, association.owner_id)
        with translate_database_errors("associate memory and entity"):
            _require_live_memory(self._session, scope, association.memory_id)
            _require_active_entity(self._session, scope, association.entity_id)
            self._session.add(
                MemoryEntityRow(
                    id=association.id,
                    owner_id=association.owner_id,
                    memory_id=association.memory_id,
                    entity_id=association.entity_id,
                    role=association.role.value,
                )
            )
            self._session.flush()

    def entities_of_memory(
        self, scope: OwnerScope, memory_id: uuid.UUID
    ) -> Sequence[MemoryEntityAssociation]:
        return self._associations(scope, MemoryEntityRow.memory_id == memory_id)

    def memories_of_entity(
        self, scope: OwnerScope, entity_id: uuid.UUID
    ) -> Sequence[MemoryEntityAssociation]:
        return self._associations(scope, MemoryEntityRow.entity_id == entity_id)

    def _associations(
        self, scope: OwnerScope, condition: ColumnElement[bool]
    ) -> Sequence[MemoryEntityAssociation]:
        with translate_database_errors("list memory-entity associations"):
            rows = self._session.scalars(
                select(MemoryEntityRow)
                .where(MemoryEntityRow.owner_id == scope.owner_id, condition)
                .order_by(MemoryEntityRow.created_at, MemoryEntityRow.id)
            ).all()
        return [_association(row) for row in rows]

    def _close(
        self,
        model: type[EntityRelationshipRow] | type[MemoryRelationshipRow],
        scope: OwnerScope,
        relationship_id: uuid.UUID,
        valid_to: datetime | None,
        superseded_at: datetime,
    ) -> None:
        if superseded_at.utcoffset() is None or (
            valid_to is not None and valid_to.utcoffset() is None
        ):
            raise DomainValidationError("closing times must be timezone-aware")
        with translate_database_errors("close relationship"):
            conditional_update(
                self._session,
                update(model)
                .where(
                    model.id == relationship_id,
                    model.owner_id == scope.owner_id,
                    model.superseded_at.is_(None),
                )
                .values(valid_to=valid_to, superseded_at=superseded_at),
                exists=select(model.id)
                .where(model.id == relationship_id, model.owner_id == scope.owner_id)
                .exists(),
                what="relationship",
            )
