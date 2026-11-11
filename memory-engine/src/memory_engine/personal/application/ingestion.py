"""Personal memory ingestion: text and conversations (plan 8.3 section 5; algorithm 6.2.1).

Flow, with owner-approved choices from 8.3 step 2:

1. Check the request belongs to the caller's owner scope.
2. Validate and normalize it. Rejections raise :class:`IngestionRejectedError`
   with an ``outcome`` and a reason code, and store nothing.
3. Replay: a known idempotency key returns the existing source, or raises
   :class:`IdempotencyKeyReusedError` if the request differs.
4. Store the original and the normalized representation in object storage, then
   record the Memory Source as ``validated``. If the record cannot be written,
   the uploaded objects are removed (7.2 section 11).

Nothing here extracts memories. Explicit forget instructions are stored and
marked, never handed to extraction; plan 8.10 resolves them. Documents are not
accepted here: they go through document ingestion (Decision 13).
"""

import contextlib
import hashlib
import io
import json
import unicodedata
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from memory_engine.domain.errors import OwnershipError
from memory_engine.domain.identifiers import OwnerScope, new_id
from memory_engine.domain.object_storage import ObjectStorage
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
from memory_engine.personal.application.ports import PersonalUnitOfWorkFactory
from memory_engine.personal.domain import MemorySource

SCHEMA_VERSION = "1"
NORMALIZATION_VERSION = "1"
_KEEP_CONTROL = frozenset("\n\t")


@dataclass(frozen=True, slots=True, kw_only=True)
class ConversationMessage:
    """One message, kept separate from the others (6.2.1: never flattened)."""

    speaker: str
    from_user: bool
    text: str
    message_id: str | None = None
    sent_at: datetime | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class IngestionRequest:
    """The logical ingestion contract (plan 8.3 section 7; 6.2.1 section 3.3).

    ``text`` for ``SourceType.TEXT``; ``messages`` for ``SourceType.CONVERSATION``.
    """

    owner_id: uuid.UUID
    idempotency_key: str
    source_type: SourceType
    instruction_type: InstructionType = InstructionType.NORMAL
    text: str | None = None
    messages: Sequence[ConversationMessage] = ()
    conversation_id: str | None = None
    source_ref: str | None = None
    source_timestamp: datetime | None = None
    priority_hint: IngestionPriority | None = None
    schema_version: str = SCHEMA_VERSION


@dataclass(frozen=True, slots=True, kw_only=True)
class IngestionLimits:
    max_text_bytes: int
    max_conversation_messages: int
    max_conversation_bytes: int


@dataclass(frozen=True, slots=True, kw_only=True)
class IngestionResult:
    """An accurate acknowledgement: accepted and stored, not yet processed (6.2.1 step 10)."""

    source_id: uuid.UUID
    status: SourceProcessingStatus
    instruction_type: InstructionType
    priority: IngestionPriority
    created: bool


@dataclass(frozen=True, slots=True)
class _Prepared:
    original: bytes
    original_type: str
    normalized: bytes
    fingerprint: str
    priority: IngestionPriority


def _reject(outcome: str, reason: str) -> IngestionRejectedError:
    return IngestionRejectedError(
        f"Input rejected: {reason}", details={"outcome": outcome, "reason": reason}
    )


def _invalid(reason: str) -> IngestionRejectedError:
    return _reject("invalid_input", reason)


def normalize_text(value: str) -> str:
    """Normalize without changing meaning (6.2.1 step 6).

    Unicode NFC, line endings to ``\\n``, control characters removed except
    newline and tab, and surrounding whitespace trimmed. Punctuation, negations
    and inner whitespace are untouched.
    """
    text = unicodedata.normalize("NFC", value).replace("\r\n", "\n").replace("\r", "\n")
    text = "".join(c for c in text if c in _KEEP_CONTROL or unicodedata.category(c) != "Cc")
    return text.strip()


def _utf8(value: str) -> bytes:
    try:
        return value.encode("utf-8")
    except UnicodeEncodeError as err:
        raise _invalid("INVALID_ENCODING") from err


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.utcoffset() is None:
        raise _invalid("NAIVE_TIMESTAMP")
    return value.isoformat()


def _optional_ref(value: str | None, reason: str, max_length: int) -> str | None:
    if value is not None and (not value.strip() or len(value) > max_length):
        raise _invalid(reason)
    return value


def prepare(request: IngestionRequest, limits: IngestionLimits) -> _Prepared:
    """Validate and normalize a request; raises ``IngestionRejectedError``."""
    if request.schema_version != SCHEMA_VERSION:
        raise _reject("unsupported_input", "UNSUPPORTED_SCHEMA_VERSION")
    if request.source_type not in (SourceType.TEXT, SourceType.CONVERSATION):
        raise _reject("unsupported_input", "UNSUPPORTED_SOURCE_TYPE")
    key = request.idempotency_key
    if not key.strip() or len(key) > 200:
        raise _invalid("INVALID_IDEMPOTENCY_KEY")
    _optional_ref(request.source_ref, "INVALID_SOURCE_REF", 500)
    _optional_ref(request.conversation_id, "INVALID_CONVERSATION_ID", 500)
    common = {
        "schema_version": request.schema_version,
        "source_type": request.source_type.value,
        "instruction_type": request.instruction_type.value,
        "priority_hint": None if request.priority_hint is None else request.priority_hint.value,
        "source_ref": request.source_ref,
        "source_timestamp": _iso(request.source_timestamp),
    }
    if request.source_type is SourceType.TEXT:
        if request.text is None or request.messages or request.conversation_id is not None:
            raise _invalid("TEXT_REQUIRED")
        original = _utf8(request.text)
        if len(original) > limits.max_text_bytes:
            raise _invalid("CONTENT_TOO_LARGE")
        normalized_text = normalize_text(request.text)
        if not normalized_text:
            raise _invalid("EMPTY_CONTENT")
        content: dict[str, Any] = {"text": request.text}
        normalized_content: dict[str, Any] = {"text": normalized_text}
        original_type = "text/plain; charset=utf-8"
    else:
        if request.text is not None or not request.messages:
            raise _invalid("MESSAGES_REQUIRED")
        if len(request.messages) > limits.max_conversation_messages:
            raise _invalid("TOO_MANY_MESSAGES")
        messages, normalized_messages = _conversation(request.messages)
        content = {"conversation_id": request.conversation_id, "messages": messages}
        normalized_content = {
            "conversation_id": request.conversation_id,
            "messages": normalized_messages,
        }
        original = _canonical(content)
        if len(original) > limits.max_conversation_bytes:
            raise _invalid("CONTENT_TOO_LARGE")
        original_type = "application/json"
    explicit = request.instruction_type is not InstructionType.NORMAL
    priority = (
        IngestionPriority.HIGH
        if explicit or request.priority_hint is IngestionPriority.HIGH
        else IngestionPriority.NORMAL
    )
    normalized = _canonical(
        {**common, "normalization_version": NORMALIZATION_VERSION, **normalized_content}
    )
    fingerprint = hashlib.sha256(_canonical({**common, **content})).hexdigest()
    return _Prepared(original, original_type, normalized, fingerprint, priority)


def _conversation(
    messages: Sequence[ConversationMessage],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    seen: set[str] = set()
    originals: list[dict[str, Any]] = []
    normalized: list[dict[str, Any]] = []
    for position, message in enumerate(messages):
        if not message.speaker.strip() or len(message.speaker) > 200:
            raise _invalid("INVALID_SPEAKER")
        if message.message_id is not None:
            if not message.message_id.strip() or message.message_id in seen:
                raise _invalid("INVALID_MESSAGE_ID")
            seen.add(message.message_id)
        _utf8(message.text)
        text = normalize_text(message.text)
        if not text:
            raise _invalid("EMPTY_MESSAGE")
        base = {
            "position": position,  # original order, kept explicitly
            "message_id": message.message_id,
            "speaker": message.speaker,
            "from_user": message.from_user,
            "sent_at": _iso(message.sent_at),
        }
        originals.append({**base, "text": message.text})
        normalized.append({**base, "speaker": normalize_text(message.speaker), "text": text})
    return originals, normalized


def source_keys(owner_id: uuid.UUID, source_id: uuid.UUID) -> tuple[str, str]:
    """Object keys of a source's original and normalized content."""
    base = f"memory-sources/{owner_id}/{source_id}"
    return f"{base}/original", f"{base}/normalized"


def _utc_now() -> datetime:
    return datetime.now(UTC)


class PersonalIngestionService:
    def __init__(
        self,
        uow_factory: PersonalUnitOfWorkFactory,
        storage: ObjectStorage,
        limits: IngestionLimits,
        *,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._uow_factory = uow_factory
        self._storage = storage
        self._limits = limits
        self._clock = clock

    def ingest(self, scope: OwnerScope, request: IngestionRequest) -> IngestionResult:
        if not scope.owns(request.owner_id):
            raise OwnershipError("ingestion request belongs to a different owner scope")
        prepared = prepare(request, self._limits)
        existing = self._existing(scope, request.idempotency_key)
        if existing is not None:
            return _replay(existing, prepared)

        source_id = new_id()
        original_key, normalized_key = source_keys(scope.owner_id, source_id)
        self._store(scope, original_key, prepared.original, prepared.original_type)
        try:
            self._store(scope, normalized_key, prepared.normalized, "application/json")
        except ObjectStorageError:
            self._discard(scope, original_key)
            raise
        source = MemorySource(
            id=source_id,
            owner_id=scope.owner_id,
            source_type=request.source_type,
            processing_status=SourceProcessingStatus.VALIDATED,
            received_at=self._clock(),
            content_ref=original_key,
            content_sha256=hashlib.sha256(prepared.original).hexdigest(),
            instruction_type=request.instruction_type,
            priority=prepared.priority,
            idempotency_key=request.idempotency_key,
            request_sha256=prepared.fingerprint,
            source_ref=request.source_ref,
            source_timestamp=request.source_timestamp,
            normalized_ref=normalized_key,
        )
        try:
            with self._uow_factory() as uow:
                uow.sources.add(scope, source)
        except PersistenceError:
            self._discard(scope, original_key, normalized_key)
            # A concurrent request with the same key may have won the race.
            winner = self._existing(scope, request.idempotency_key)
            if winner is not None:
                return _replay(winner, prepared)
            raise
        return IngestionResult(
            source_id=source_id,
            status=source.processing_status,
            instruction_type=source.instruction_type,
            priority=source.priority,
            created=True,
        )

    def _existing(self, scope: OwnerScope, key: str) -> MemorySource | None:
        with self._uow_factory() as uow:
            return uow.sources.find_by_idempotency_key(scope, key)

    def _store(self, scope: OwnerScope, key: str, data: bytes, content_type: str) -> None:
        self._storage.put(
            scope,
            key,
            io.BytesIO(data),
            content_type=content_type,
            size_bytes=len(data),
            sha256=hashlib.sha256(data).hexdigest(),
        )

    def _discard(self, scope: OwnerScope, *keys: str) -> None:
        # Best effort: an object left behind here has no record pointing at it and
        # is found by reconciliation (7.2 section 11); the original error matters more.
        for key in keys:
            with contextlib.suppress(ObjectStorageError):
                self._storage.delete(scope, key)


def _replay(existing: MemorySource, prepared: _Prepared) -> IngestionResult:
    if existing.request_sha256 != prepared.fingerprint:
        raise IdempotencyKeyReusedError("idempotency key was already used for another request")
    return IngestionResult(
        source_id=existing.id,
        status=existing.processing_status,
        instruction_type=existing.instruction_type,
        priority=existing.priority,
        created=False,
    )
