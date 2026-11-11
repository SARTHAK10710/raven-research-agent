"""Phase 8.3 step 4: the handoff contract, topology, Celery wiring and relay policy.

No broker or database: the Celery publisher is exercised against a stand-in app.
"""

import importlib.util
import json
import uuid
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from kombu.exceptions import OperationalError
from pydantic import SecretStr

from memory_engine.config.settings import BrokerSettings, OutboxSettings
from memory_engine.documents.application.ingestion import (
    extraction_handoff as document_handoff,
)
from memory_engine.documents.domain import DocumentVersion, ProcessingOperation
from memory_engine.documents.domain.vocabulary import (
    DocumentMediaType,
    OperationStatus,
    OperationType,
    VersionProcessingStatus,
)
from memory_engine.domain.errors import DomainValidationError, OwnershipError
from memory_engine.domain.handoff import (
    ENVELOPE_SCHEMA_VERSION,
    HandoffEnvelope,
    HandoffKind,
    OutboxMessage,
    OutboxStatus,
)
from memory_engine.domain.identifiers import OwnerScope, new_id
from memory_engine.domain.vocabulary import (
    IngestionPriority,
    InstructionType,
    SourceProcessingStatus,
    SourceType,
)
from memory_engine.exceptions import MessagePublishError
from memory_engine.infrastructure.messaging import (
    EXCHANGE_NAME,
    ROUTES,
    CeleryPublisher,
    RelayOutcome,
    RelayReport,
    backoff_seconds,
    build_broker_url,
    create_celery_app,
)
from memory_engine.infrastructure.messaging.relay import jittered
from memory_engine.infrastructure.persistence import outbox as outbox_models
from memory_engine.infrastructure.persistence.outbox import SqlAlchemyOutboxRepository
from memory_engine.personal.application.ingestion import (
    extraction_handoff as personal_handoff,
)
from memory_engine.personal.domain import MemorySource

T0 = datetime(2026, 11, 12, 9, 0, tzinfo=UTC)
OWNER = OwnerScope(uuid.UUID("00000000-0000-4000-8000-000000000001"))
MIGRATION_0008 = (
    Path(__file__).resolve().parents[3]
    / "memory-engine"
    / "migrations"
    / "versions"
    / "20261112_0008_outbox.py"
)


def _source(instruction: InstructionType = InstructionType.NORMAL) -> MemorySource:
    source_id = new_id()
    return MemorySource(
        id=source_id,
        owner_id=OWNER.owner_id,
        source_type=SourceType.TEXT,
        processing_status=SourceProcessingStatus.VALIDATED,
        received_at=T0,
        content_ref=f"memory-sources/{OWNER.owner_id}/{source_id}/original",
        content_sha256="a" * 64,
        instruction_type=instruction,
        priority=(
            IngestionPriority.NORMAL
            if instruction is InstructionType.NORMAL
            else IngestionPriority.HIGH
        ),
        idempotency_key="k-1",
        request_sha256="b" * 64,
        normalized_ref=f"memory-sources/{OWNER.owner_id}/{source_id}/normalized",
    )


def _message(**overrides: Any) -> OutboxMessage:
    message = personal_handoff(OWNER, _source())
    assert message is not None
    return replace(message, **overrides)


# --- contract ---------------------------------------------------------------------


def test_the_envelope_round_trips_through_json() -> None:
    envelope = _message().envelope
    wire = json.loads(json.dumps(envelope.to_dict()))
    assert HandoffEnvelope.from_dict(wire) == envelope
    assert wire["schema_version"] == ENVELOPE_SCHEMA_VERSION == "1"
    assert wire["message_type"] == "command"
    assert wire["source_component"] == "memory_engine.ingestion"
    assert wire["destination_component"] == "memory_engine.extraction"
    # Every 7.4 section 7 field is present on the wire.
    assert set(wire) >= {
        "message_id",
        "execution_id",
        "task_id",
        "user_id",
        "source_component",
        "destination_component",
        "message_type",
        "operation",
        "created_at",
        "correlation_id",
        "causation_id",
        "schema_version",
        "payload_reference",
        "priority",
        "idempotency_key",
        "trace_context",
    }


def test_a_personal_handoff_references_content_and_never_carries_it() -> None:
    source = _source(InstructionType.REMEMBER)
    message = personal_handoff(OWNER, source)
    assert message is not None
    envelope = message.envelope
    assert message.kind is HandoffKind.PERSONAL_EXTRACTION
    assert message.subject_id == envelope.task_id == source.id
    assert message.status is OutboxStatus.PENDING and message.attempts == 0
    assert envelope.user_id == OWNER.owner_id
    assert envelope.priority == "high"  # explicit remember is prioritized (5.4)
    assert envelope.payload_reference == source.content_ref
    assert dict(envelope.payload) == {
        "source_id": str(source.id),
        "source_type": "text",
        "instruction_type": "remember",
        "normalized_ref": source.normalized_ref,
    }
    assert envelope.idempotency_key == f"personal_extraction:{source.id}"
    assert envelope.correlation_id == envelope.message_id


def test_a_forget_instruction_gets_no_handoff_to_extraction() -> None:
    assert personal_handoff(OWNER, _source(InstructionType.FORGET)) is None


def test_a_document_handoff_names_the_version_operation_and_original() -> None:
    document_id, version_id = new_id(), new_id()
    version = DocumentVersion(
        id=version_id,
        owner_id=OWNER.owner_id,
        document_id=document_id,
        version_number=1,
        object_key=DocumentVersion.object_key_for(OWNER.owner_id, document_id, version_id),
        content_sha256="c" * 64,
        size_bytes=42,
        media_type=DocumentMediaType.PDF,
        uploaded_at=T0,
        processing_status=VersionProcessingStatus.STORED,
    )
    operation = ProcessingOperation(
        id=new_id(),
        owner_id=OWNER.owner_id,
        document_id=document_id,
        version_id=version_id,
        operation_type=OperationType.EXTRACTION,
        status=OperationStatus.CREATED,
        idempotency_key="upload:k",
    )
    message = document_handoff(OWNER, operation, version)
    envelope = message.envelope
    assert message.kind is HandoffKind.DOCUMENT_EXTRACTION
    assert message.subject_id == operation.id
    assert envelope.destination_component == "memory_engine.document_pipeline"
    assert envelope.payload_reference == version.object_key
    assert dict(envelope.payload) == {
        "document_id": str(document_id),
        "version_id": str(version_id),
        "operation_id": str(operation.id),
        "operation_type": "extraction",
        "media_type": "application/pdf",
        "content_sha256": "c" * 64,
        "size_bytes": "42",
    }


@pytest.mark.parametrize(
    ("change", "value"),
    [
        ("schema_version", "2"),
        ("schema_version", None),
        ("operation", "personal_deletion"),
        ("destination_component", "memory_engine.document_pipeline"),
        ("message_id", "not-a-uuid"),
        ("user_id", None),
        ("created_at", "yesterday"),
        ("created_at", "2026-11-12T09:00:00"),  # naive
        ("payload", ["not", "a", "mapping"]),
        ("trace_context", "nope"),
        ("payload", {"Bad Key": "x"}),
        ("payload", {"text": "x" * 513}),
        ("payload", {"count": 3}),
        ("priority", "urgent"),
        ("message_type", "event"),
        ("idempotency_key", "   "),
        ("source_component", 7),
    ],
)
def test_invalid_envelopes_are_refused(change: str, value: Any) -> None:
    wire = _message().envelope.to_dict()
    wire[change] = value
    with pytest.raises(DomainValidationError):
        HandoffEnvelope.from_dict(wire)


def test_an_overlong_idempotency_key_is_refused() -> None:
    with pytest.raises(DomainValidationError, match="idempotency_key"):
        replace(_message().envelope, idempotency_key="k" * 201)


def test_an_empty_source_component_is_refused() -> None:
    with pytest.raises(DomainValidationError, match="source_component"):
        replace(_message().envelope, source_component=" ")


def test_envelope_payload_is_read_only() -> None:
    envelope = _message().envelope
    with pytest.raises(TypeError):
        envelope.payload["source_id"] = "x"  # type: ignore[index]


@pytest.mark.parametrize(
    "overrides",
    [
        {"attempts": -1},
        {"last_error_code": "lower case"},
        {"status": OutboxStatus.PUBLISHED},
        {"published_at": T0},
        {"next_attempt_at": datetime(2026, 11, 12, 9, 0)},
        {"owner_id": uuid.uuid4()},
        {"id": uuid.uuid4()},
        {"kind": HandoffKind.DOCUMENT_EXTRACTION},
        {"subject_id": uuid.uuid4()},
    ],
    ids=lambda o: next(iter(o)),
)
def test_outbox_message_invariants(overrides: dict[str, Any]) -> None:
    with pytest.raises(DomainValidationError):
        _message(**overrides)


def test_a_published_message_needs_its_publication_time() -> None:
    published = _message(status=OutboxStatus.PUBLISHED, published_at=T0)
    assert published.published_at == T0


def test_the_outbox_refuses_a_message_of_another_owner() -> None:
    repository = SqlAlchemyOutboxRepository(session=None)  # type: ignore[arg-type]
    with pytest.raises(OwnershipError):
        repository.add(OwnerScope(uuid.uuid4()), _message())


# --- topology and Celery wiring -----------------------------------------------------


def test_every_handoff_kind_has_its_own_queue_and_routing_key() -> None:
    assert set(ROUTES) == set(HandoffKind)
    routes = list(ROUTES.values())
    assert len({r.queue for r in routes}) == len({r.routing_key for r in routes}) == 2
    assert len({r.task_name for r in routes}) == 2
    assert ROUTES[HandoffKind.DOCUMENT_EXTRACTION].queue == "memory.document.processing"
    assert ROUTES[HandoffKind.PERSONAL_EXTRACTION].queue == "memory.personal.extraction"
    assert ROUTES[HandoffKind.DOCUMENT_EXTRACTION].routing_key == "document.extraction.requested"
    assert ROUTES[HandoffKind.PERSONAL_EXTRACTION].routing_key == "personal.extraction.requested"


def _broker(**overrides: Any) -> BrokerSettings:
    values: dict[str, Any] = {
        "host": "broker.test.invalid",
        "virtual_host": "raven_test",
        "user": "raven publisher",
        "password": SecretStr("p@ss/word:1"),
    }
    return BrokerSettings.model_validate(values | overrides)


def test_broker_url_quotes_credentials_and_selects_tls() -> None:
    assert (
        build_broker_url(_broker())
        == "amqp://raven%20publisher:p%40ss%2Fword%3A1@broker.test.invalid:5672/raven_test"
    )
    assert build_broker_url(_broker(use_tls=True, port=5671)).startswith("amqps://")


def test_broker_password_is_masked_and_required() -> None:
    assert "p@ss" not in repr(_broker())
    with pytest.raises(ValueError, match="must not be empty"):
        _broker(password=SecretStr(""))


def test_celery_app_uses_safe_defaults_and_the_handoff_topology() -> None:
    app = create_celery_app(_broker())
    conf = app.conf
    assert conf.task_serializer == "json" and list(conf.accept_content) == ["json"]
    assert conf.task_acks_late is True and conf.task_reject_on_worker_lost is True
    assert conf.worker_prefetch_multiplier == 1
    assert conf.task_ignore_result is True and not conf.result_backend
    assert conf.broker_transport_options == {"confirm_publish": True}
    assert conf.task_publish_retry is False and conf.task_create_missing_queues is False
    queues = {q.name: q for q in conf.task_queues}
    assert set(queues) == {r.queue for r in ROUTES.values()}
    for route in ROUTES.values():
        queue = queues[route.queue]
        assert queue.exchange.name == EXCHANGE_NAME and queue.exchange.type == "direct"
        assert queue.durable and queue.exchange.durable
        assert queue.routing_key == route.routing_key
        assert conf.task_routes[route.task_name]["queue"] == route.queue
    assert "p@ss" not in repr(conf.humanize(with_defaults=False, censored=True))


# --- relay policy -------------------------------------------------------------------


def test_backoff_doubles_from_the_base_and_is_capped() -> None:
    settings = OutboxSettings()
    assert [backoff_seconds(n, settings) for n in (1, 2, 3, 4)] == [2.0, 4.0, 8.0, 16.0]
    assert backoff_seconds(9, settings) == 300.0
    assert backoff_seconds(10_000, settings) == 300.0


def test_jitter_stays_between_half_and_the_full_delay() -> None:
    values = [jittered(10.0) for _ in range(200)]
    assert all(5.0 <= v <= 10.0 for v in values)
    assert len(set(values)) > 1


def test_relay_report_counts_outcomes() -> None:
    report = RelayReport()
    for outcome in RelayOutcome:
        report.add(outcome)
    report.add(RelayOutcome.PUBLISHED)
    assert (report.published, report.failed, report.handled) == (2, 1, 5)


def test_outbox_defaults_match_the_owner_decision() -> None:
    settings = OutboxSettings()
    assert settings.max_attempts == 10
    assert settings.backoff_base_seconds == 2.0
    assert settings.backoff_max_seconds == 300.0


# --- publisher (stand-in Celery app; no broker) -------------------------------------


class _Connection:
    def __init__(self, fail_connect: bool = False) -> None:
        self.fail_connect = fail_connect
        self.released = False

    def ensure_connection(self, **options: Any) -> None:
        assert options["max_retries"] == 0  # a single attempt; the outbox retries
        if self.fail_connect:
            raise ConnectionRefusedError("synthetic: broker down")

    def release(self) -> None:
        self.released = True


class _Amqp:
    def Producer(self, connection: _Connection) -> tuple[str, _Connection]:  # noqa: N802
        return ("producer", connection)


class _App:
    def __init__(self, *, fail_connect: bool = False, fail_send: bool = False) -> None:
        self.amqp = _Amqp()
        self.conf = type("Conf", (), {"broker_connection_timeout": 3})()
        self.connections: list[_Connection] = []
        self.sent: list[dict[str, Any]] = []
        self.fail_connect = fail_connect
        self.fail_send = fail_send

    def connection_for_write(self) -> _Connection:
        connection = _Connection(self.fail_connect)
        self.connections.append(connection)
        return connection

    def send_task(self, name: str, **options: Any) -> None:
        if self.fail_send:
            raise OperationalError("synthetic: not confirmed")
        self.sent.append({"name": name, **options})


def test_publisher_sends_the_envelope_with_its_route_and_message_id() -> None:
    app = _App()
    publisher = CeleryPublisher(app, confirm_timeout_seconds=7)
    message = _message()
    publisher.publish(message)
    publisher.publish(_message())
    route = ROUTES[HandoffKind.PERSONAL_EXTRACTION]
    sent = app.sent[0]
    assert sent["name"] == route.task_name
    assert sent["args"] == [message.envelope.to_dict()]
    assert sent["task_id"] == str(message.id)
    assert (sent["queue"], sent["exchange"], sent["routing_key"]) == (
        route.queue,
        EXCHANGE_NAME,
        route.routing_key,
    )
    assert sent["retry"] is False and sent["confirm_timeout"] == 7
    assert len(app.connections) == 1  # the connection is reused while healthy
    publisher.close()
    assert app.connections[0].released


def test_an_unconfirmed_publish_raises_and_drops_the_connection() -> None:
    app = _App(fail_send=True)
    publisher = CeleryPublisher(app, confirm_timeout_seconds=1)
    with pytest.raises(MessagePublishError):
        publisher.publish(_message())
    assert app.connections[0].released
    app.fail_send = False
    publisher.publish(_message())
    assert len(app.connections) == 2  # reconnected


def test_an_unreachable_broker_raises_a_publish_error() -> None:
    app = _App(fail_connect=True)
    publisher = CeleryPublisher(app, confirm_timeout_seconds=1)
    with pytest.raises(MessagePublishError) as caught:
        publisher.publish(_message())
    assert caught.value.code == "MESSAGE_PUBLISH_ERROR"
    assert app.connections[0].released
    publisher.close()  # nothing open: a no-op


# --- migration 0008 -------------------------------------------------------------------


def _migration() -> Any:
    spec = importlib.util.spec_from_file_location("migration_0008", MIGRATION_0008)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_0008_matches_the_model_and_enums() -> None:
    migration = _migration()
    assert tuple(k.value for k in HandoffKind) == migration.HANDOFF_KINDS
    assert tuple(s.value for s in OutboxStatus) == migration.OUTBOX_STATUSES
    assert migration.PUBLISHED_AT_RULE == outbox_models.PUBLISHED_AT_RULE
    assert migration.SAFE_LAST_ERROR == outbox_models.SAFE_LAST_ERROR
    assert migration.down_revision == "0007_source_ingestion"
    columns = set(outbox_models.OutboxRow.__table__.c.keys())
    assert set(migration.GUARDED_TABLES["me_outbox"]) <= columns
    assert "envelope" not in migration.GUARDED_TABLES["me_outbox"]  # the message is immutable


def test_a_missing_required_envelope_field_is_refused() -> None:
    wire = _message().envelope.to_dict()
    del wire["priority"]
    with pytest.raises(DomainValidationError, match="priority is missing"):
        HandoffEnvelope.from_dict(wire)


def test_an_envelope_cannot_be_built_with_another_schema_version() -> None:
    with pytest.raises(DomainValidationError, match="schema_version"):
        replace(_message().envelope, schema_version="2")


def test_closing_a_publisher_tolerates_a_broken_connection() -> None:
    app = _App()
    publisher = CeleryPublisher(app, confirm_timeout_seconds=1)
    publisher.publish(_message())

    def broken() -> None:
        raise ConnectionResetError("synthetic: connection already gone")

    app.connections[0].release = broken  # type: ignore[method-assign]
    publisher.close()
    publisher.publish(_message())  # reconnects after the broken close
    assert len(app.connections) == 2


def test_the_relay_clock_is_utc() -> None:
    from memory_engine.infrastructure.messaging.relay import _utc_now

    assert _utc_now().utcoffset() == timedelta(0)
