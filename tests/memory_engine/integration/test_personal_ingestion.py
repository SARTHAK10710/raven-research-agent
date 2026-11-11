"""Phase 8.3 step 2: personal memory ingestion against real PostgreSQL.

Object storage is the in-memory fake (the S3 adapter has its own integration
tests). All content is synthetic.
"""

import json
from datetime import UTC, datetime
from typing import Any, BinaryIO

import pytest
from sqlalchemy import Connection, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from memory_engine.domain.errors import OwnershipError
from memory_engine.domain.identifiers import OwnerScope
from memory_engine.domain.object_storage import StoredObject
from memory_engine.domain.vocabulary import (
    IngestionPriority,
    InstructionType,
    SourceProcessingStatus,
    SourceType,
)
from memory_engine.exceptions import (
    IdempotencyKeyReusedError,
    IngestionRejectedError,
    ObjectStorageError,
    PersistenceError,
)
from memory_engine.infrastructure.object_storage import InMemoryObjectStorage
from memory_engine.infrastructure.persistence import SqlAlchemyPersonalUnitOfWorkFactory
from memory_engine.infrastructure.persistence.personal.repositories import (
    SqlAlchemyMemorySourceRepository,
)
from memory_engine.personal.application.ingestion import (
    ConversationMessage,
    IngestionLimits,
    IngestionRequest,
    PersonalIngestionService,
)

pytestmark = pytest.mark.integration

Uow = SqlAlchemyPersonalUnitOfWorkFactory
T0 = datetime(2026, 11, 1, 9, 0, tzinfo=UTC)
LIMITS = IngestionLimits(
    max_text_bytes=256 * 1024, max_conversation_messages=1000, max_conversation_bytes=4 * 1024**2
)


def _service(uow_factory: Uow, storage: Any) -> PersonalIngestionService:
    return PersonalIngestionService(uow_factory, storage, LIMITS, clock=lambda: T0)


def _text(owner: OwnerScope, key: str = "msg-1", **overrides: Any) -> IngestionRequest:
    values: dict[str, Any] = {
        "owner_id": owner.owner_id,
        "idempotency_key": key,
        "source_type": SourceType.TEXT,
        "text": "Remember that I prefer window seats.",
    }
    return IngestionRequest(**values | overrides)


def _keys(storage: InMemoryObjectStorage) -> set[str]:
    return set(storage._objects)  # test-only inspection of the fake


def test_text_is_stored_and_registered_but_not_processed(
    uow_factory: Uow, owner: OwnerScope
) -> None:
    storage = InMemoryObjectStorage()
    result = _service(uow_factory, storage).ingest(
        owner,
        _text(owner, instruction_type=InstructionType.REMEMBER, source_ref="app-msg-42"),
    )
    assert result.created and result.status is SourceProcessingStatus.VALIDATED
    assert result.priority is IngestionPriority.HIGH
    with uow_factory() as uow:
        source = uow.sources.get(owner, result.source_id)
        assert uow.candidates.list_for_source(owner, result.source_id) == []  # AC-16
    assert source is not None
    assert (source.received_at, source.source_ref) == (T0, "app-msg-42")
    assert source.content_ref is not None and source.normalized_ref is not None
    assert storage.get(owner, source.content_ref) == b"Remember that I prefer window seats."
    normalized = json.loads(storage.get(owner, source.normalized_ref))
    assert normalized["instruction_type"] == "remember"
    assert _keys(storage) == {source.content_ref, source.normalized_ref}


def test_a_retry_returns_the_same_source_without_storing_again(
    uow_factory: Uow, owner: OwnerScope
) -> None:
    storage = InMemoryObjectStorage()
    service = _service(uow_factory, storage)
    first = service.ingest(owner, _text(owner))
    stored = _keys(storage)
    again = service.ingest(owner, _text(owner))
    assert (again.source_id, again.created) == (first.source_id, False)
    assert _keys(storage) == stored
    with pytest.raises(IdempotencyKeyReusedError):
        service.ingest(owner, _text(owner, text="Something else entirely."))
    assert _keys(storage) == stored


def test_idempotency_keys_are_per_owner(
    uow_factory: Uow, owner: OwnerScope, other_owner: OwnerScope
) -> None:
    service = _service(uow_factory, InMemoryObjectStorage())
    mine = service.ingest(owner, _text(owner))
    theirs = service.ingest(other_owner, _text(other_owner))
    assert mine.source_id != theirs.source_id and theirs.created


def test_conversation_keeps_messages_separate_and_ordered(
    uow_factory: Uow, owner: OwnerScope
) -> None:
    storage = InMemoryObjectStorage()
    result = _service(uow_factory, storage).ingest(
        owner,
        IngestionRequest(
            owner_id=owner.owner_id,
            idempotency_key="conv-1",
            source_type=SourceType.CONVERSATION,
            conversation_id="chat-7",
            messages=(
                ConversationMessage(speaker="Alex", from_user=False, text="I live in Lyon."),
                ConversationMessage(speaker="me", from_user=True, text="I live in Berlin."),
            ),
        ),
    )
    with uow_factory() as uow:
        source = uow.sources.get(owner, result.source_id)
    assert source is not None and source.source_type is SourceType.CONVERSATION
    assert source.normalized_ref is not None
    messages = json.loads(storage.get(owner, source.normalized_ref))["messages"]
    assert [(m["speaker"], m["from_user"], m["text"]) for m in messages] == [
        ("Alex", False, "I live in Lyon."),
        ("me", True, "I live in Berlin."),
    ]


def test_a_forget_instruction_is_recorded_and_never_queued_for_extraction(
    uow_factory: Uow, owner: OwnerScope
) -> None:
    result = _service(uow_factory, InMemoryObjectStorage()).ingest(
        owner,
        _text(owner, text="Forget my old address.", instruction_type=InstructionType.FORGET),
    )
    with uow_factory() as uow:
        source = uow.sources.get(owner, result.source_id)
    assert source is not None
    assert source.instruction_type is InstructionType.FORGET
    assert source.priority is IngestionPriority.HIGH
    # Stays validated: nothing deletes yet (8.10), and step 4 routes forget away from extraction.
    assert source.processing_status is SourceProcessingStatus.VALIDATED


def test_rejected_and_foreign_requests_store_nothing(
    uow_factory: Uow, owner: OwnerScope, other_owner: OwnerScope
) -> None:
    storage = InMemoryObjectStorage()
    service = _service(uow_factory, storage)
    with pytest.raises(IngestionRejectedError):
        service.ingest(owner, _text(owner, text="   "))
    with pytest.raises(OwnershipError):
        service.ingest(owner, _text(other_owner))
    assert _keys(storage) == set()
    with uow_factory() as uow:
        assert uow.sources.find_by_idempotency_key(owner, "msg-1") is None


def test_a_storage_outage_registers_nothing(uow_factory: Uow, owner: OwnerScope) -> None:
    storage = InMemoryObjectStorage()
    storage.available = False
    with pytest.raises(ObjectStorageError):
        _service(uow_factory, storage).ingest(owner, _text(owner))
    with uow_factory() as uow:
        assert uow.sources.find_by_idempotency_key(owner, "msg-1") is None


class _FailsOnSecondPut(InMemoryObjectStorage):
    def __init__(self) -> None:
        super().__init__()
        self.puts = 0

    def put(self, scope: OwnerScope, key: str, data: BinaryIO, **kwargs: Any) -> StoredObject:
        self.puts += 1
        if self.puts == 2:
            raise ObjectStorageError("simulated failure")
        return super().put(scope, key, data, **kwargs)


def test_a_partial_upload_is_cleaned_up(uow_factory: Uow, owner: OwnerScope) -> None:
    storage = _FailsOnSecondPut()
    with pytest.raises(ObjectStorageError):
        _service(uow_factory, storage).ingest(owner, _text(owner))
    assert _keys(storage) == set()


def test_a_failed_registration_removes_the_uploaded_objects(
    uow_factory: Uow, owner: OwnerScope, monkeypatch: pytest.MonkeyPatch
) -> None:
    storage = InMemoryObjectStorage()

    def fail(self: Any, scope: OwnerScope, source: Any) -> None:
        raise PersistenceError("simulated database failure")

    monkeypatch.setattr(SqlAlchemyMemorySourceRepository, "add", fail)
    with pytest.raises(PersistenceError):
        _service(uow_factory, storage).ingest(owner, _text(owner))
    assert _keys(storage) == set()


def test_a_lost_race_on_the_same_key_returns_the_winner(
    uow_factory: Uow, owner: OwnerScope, monkeypatch: pytest.MonkeyPatch
) -> None:
    storage = InMemoryObjectStorage()
    service = _service(uow_factory, storage)
    winner = service.ingest(owner, _text(owner))
    winner_keys = _keys(storage)

    original_find = SqlAlchemyMemorySourceRepository.find_by_idempotency_key
    calls = {"n": 0}

    def find_late(self: Any, scope: OwnerScope, key: str) -> Any:
        calls["n"] += 1
        # The loser's first lookup happens before the winner committed.
        return None if calls["n"] == 1 else original_find(self, scope, key)

    monkeypatch.setattr(SqlAlchemyMemorySourceRepository, "find_by_idempotency_key", find_late)
    loser = service.ingest(owner, _text(owner))
    assert (loser.source_id, loser.created) == (winner.source_id, False)
    assert _keys(storage) == winner_keys  # the loser's uploads were removed


def test_the_database_refuses_inconsistent_ingestion_fields(
    connection: Connection, owner: OwnerScope
) -> None:
    with pytest.raises(IntegrityError, match="ck_pm_memory_source_instruction_priority"):
        connection.execute(
            text(
                "INSERT INTO memory.pm_memory_source (id, owner_id, source_type,"
                " processing_status, received_at, instruction_type, priority)"
                " VALUES (gen_random_uuid(), :o, 'text', 'validated', now(), 'forget', 'normal')"
            ),
            {"o": owner.owner_id},
        )


def test_ingestion_fields_are_immutable(
    connection: Connection, uow_factory: Uow, owner: OwnerScope
) -> None:
    result = _service(uow_factory, InMemoryObjectStorage()).ingest(owner, _text(owner))
    with pytest.raises(DBAPIError, match="immutable columns"):
        connection.execute(
            text("UPDATE memory.pm_memory_source SET instruction_type = 'forget' WHERE id = :s"),
            {"s": result.source_id},
        )
