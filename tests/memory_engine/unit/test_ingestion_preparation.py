"""Phase 8.3 step 2: validation and normalization of personal-memory inputs (no I/O)."""

import json
import uuid
from datetime import UTC, datetime
from typing import Any

import pytest

from memory_engine.domain.vocabulary import IngestionPriority, InstructionType, SourceType
from memory_engine.exceptions import IngestionRejectedError
from memory_engine.personal.application.ingestion import (
    ConversationMessage,
    IngestionLimits,
    IngestionRequest,
    normalize_text,
    prepare,
    source_keys,
)

OWNER = uuid.UUID("00000000-0000-4000-8000-000000000001")
T0 = datetime(2026, 11, 1, 9, 0, tzinfo=UTC)
LIMITS = IngestionLimits(
    max_text_bytes=64, max_conversation_messages=3, max_conversation_bytes=2048
)


def _text(**overrides: Any) -> IngestionRequest:
    values: dict[str, Any] = {
        "owner_id": OWNER,
        "idempotency_key": "msg-1",
        "source_type": SourceType.TEXT,
        "text": "I do not like coffee.",
    }
    return IngestionRequest(**values | overrides)


def _conversation(*messages: ConversationMessage, **overrides: Any) -> IngestionRequest:
    values: dict[str, Any] = {
        "owner_id": OWNER,
        "idempotency_key": "conv-1",
        "source_type": SourceType.CONVERSATION,
        "conversation_id": "chat-7",
        "messages": messages,
    }
    return IngestionRequest(**values | overrides)


def _message(speaker: str, text: str, *, from_user: bool, **extra: Any) -> ConversationMessage:
    return ConversationMessage(speaker=speaker, from_user=from_user, text=text, **extra)


def _reason(request: IngestionRequest, limits: IngestionLimits = LIMITS) -> tuple[str, str]:
    with pytest.raises(IngestionRejectedError) as caught:
        prepare(request, limits)
    details = caught.value.details
    assert "coffee" not in str(caught.value)  # messages never carry the input
    return details["outcome"], details["reason"]


# --- normalization -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("  I do not like coffee.  ", "I do not like coffee."),
        ("line one\r\nline two\rline three", "line one\nline two\nline three"),
        ("tab\tkept\x00\x07 bell removed", "tab\tkept bell removed"),
        ("café", "café"),  # NFC
        ("Maybe I'll move to Berlin?", "Maybe I'll move to Berlin?"),
    ],
)
def test_normalization_keeps_meaning(raw: str, expected: str) -> None:
    assert normalize_text(raw) == expected


def test_original_and_normalized_text_stay_distinct() -> None:
    prepared = prepare(_text(text="  I do NOT like coffee.\r\n"), LIMITS)
    assert prepared.original == b"  I do NOT like coffee.\r\n"
    normalized = json.loads(prepared.normalized)
    assert normalized["text"] == "I do NOT like coffee."
    assert normalized["normalization_version"] == "1"
    assert prepared.original_type == "text/plain; charset=utf-8"


# --- priority and fingerprint --------------------------------------------------------


@pytest.mark.parametrize(
    ("instruction", "hint", "expected"),
    [
        (InstructionType.NORMAL, None, IngestionPriority.NORMAL),
        (InstructionType.NORMAL, IngestionPriority.HIGH, IngestionPriority.HIGH),
        (InstructionType.REMEMBER, None, IngestionPriority.HIGH),
        (InstructionType.FORGET, IngestionPriority.NORMAL, IngestionPriority.HIGH),
    ],
)
def test_explicit_instructions_are_high_priority(
    instruction: InstructionType, hint: IngestionPriority | None, expected: IngestionPriority
) -> None:
    prepared = prepare(_text(instruction_type=instruction, priority_hint=hint), LIMITS)
    assert prepared.priority is expected


def test_fingerprint_identifies_the_request_not_the_key() -> None:
    first = prepare(_text(), LIMITS).fingerprint
    assert prepare(_text(idempotency_key="msg-2"), LIMITS).fingerprint == first
    assert prepare(_text(text="I like tea."), LIMITS).fingerprint != first
    assert prepare(_text(instruction_type=InstructionType.FORGET), LIMITS).fingerprint != first
    assert prepare(_text(source_timestamp=T0), LIMITS).fingerprint != first


# --- conversations -------------------------------------------------------------------


def test_conversation_order_speakers_and_authorship_are_preserved() -> None:
    prepared = prepare(
        _conversation(
            _message("Alex", "My sister lives in Lyon.", from_user=False, message_id="m1"),
            _message("me", "I moved to Berlin.\r\n", from_user=True, message_id="m2", sent_at=T0),
        ),
        LIMITS,
    )
    normalized = json.loads(prepared.normalized)
    assert [m["position"] for m in normalized["messages"]] == [0, 1]
    assert [(m["speaker"], m["from_user"]) for m in normalized["messages"]] == [
        ("Alex", False),
        ("me", True),
    ]
    assert normalized["messages"][1]["text"] == "I moved to Berlin."
    assert normalized["messages"][1]["sent_at"] == T0.isoformat()
    original = json.loads(prepared.original)
    assert original["messages"][1]["text"] == "I moved to Berlin.\r\n"
    assert original["conversation_id"] == "chat-7"


# --- rejections ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("request_", "expected"),
    [
        (_text(source_type=SourceType.DOCUMENT), ("unsupported_input", "UNSUPPORTED_SOURCE_TYPE")),
        (_text(schema_version="2"), ("unsupported_input", "UNSUPPORTED_SCHEMA_VERSION")),
        (_text(idempotency_key=" "), ("invalid_input", "INVALID_IDEMPOTENCY_KEY")),
        (_text(idempotency_key="k" * 201), ("invalid_input", "INVALID_IDEMPOTENCY_KEY")),
        (_text(text=None), ("invalid_input", "TEXT_REQUIRED")),
        (_text(text=" \t\r\n "), ("invalid_input", "EMPTY_CONTENT")),
        (_text(text="\x00\x01"), ("invalid_input", "EMPTY_CONTENT")),
        (_text(text="caf\udce9"), ("invalid_input", "INVALID_ENCODING")),
        (_text(text="x" * 65), ("invalid_input", "CONTENT_TOO_LARGE")),
        (_text(source_ref=" "), ("invalid_input", "INVALID_SOURCE_REF")),
        (_text(source_timestamp=datetime(2026, 11, 1)), ("invalid_input", "NAIVE_TIMESTAMP")),
        (_conversation(), ("invalid_input", "MESSAGES_REQUIRED")),
        (
            _conversation(_message("me", "hi", from_user=True), text="also text"),
            ("invalid_input", "MESSAGES_REQUIRED"),
        ),
        (
            _conversation(*[_message("me", "hi", from_user=True)] * 4),
            ("invalid_input", "TOO_MANY_MESSAGES"),
        ),
        (
            _conversation(_message(" ", "hi", from_user=True)),
            ("invalid_input", "INVALID_SPEAKER"),
        ),
        (
            _conversation(_message("me", "  ", from_user=True)),
            ("invalid_input", "EMPTY_MESSAGE"),
        ),
        (
            _conversation(
                _message("me", "a", from_user=True, message_id="m1"),
                _message("me", "b", from_user=True, message_id="m1"),
            ),
            ("invalid_input", "INVALID_MESSAGE_ID"),
        ),
        (
            _conversation(_message("me", "x" * 3000, from_user=True)),
            ("invalid_input", "CONTENT_TOO_LARGE"),
        ),
    ],
)
def test_invalid_or_unsupported_input_is_rejected(
    request_: IngestionRequest, expected: tuple[str, str]
) -> None:
    assert _reason(request_) == expected


def test_a_text_request_cannot_carry_conversation_fields() -> None:
    assert _reason(_text(conversation_id="chat-1")) == ("invalid_input", "TEXT_REQUIRED")


def test_source_keys_are_owner_partitioned() -> None:
    source_id = uuid.uuid4()
    original, normalized = source_keys(OWNER, source_id)
    assert original == f"memory-sources/{OWNER}/{source_id}/original"
    assert normalized == f"memory-sources/{OWNER}/{source_id}/normalized"
