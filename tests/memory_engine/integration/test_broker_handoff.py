"""Phase 8.3 step 4: handoff through a real RabbitMQ broker (plan 8.3 §12.3).

Start it with ``docker compose up -d --wait broker-test``; override the target
with ``RAVEN_TEST_BROKER_URL``. The virtual host must end in ``_test``: these
tests purge the handoff queues. Messages are read back with kombu exactly as a
Celery worker would receive them. Synthetic data only.
"""

import io
import os
import uuid
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import unquote, urlsplit

import pytest
from celery import Celery
from kombu.connection import Connection
from pydantic import SecretStr
from sqlalchemy.orm import Session, sessionmaker

from memory_engine.config.settings import BrokerSettings, OutboxSettings
from memory_engine.documents.application.ingestion import (
    DocumentIngestionService,
    DocumentUpload,
)
from memory_engine.documents.domain.vocabulary import OperationStatus
from memory_engine.domain.handoff import HandoffEnvelope, HandoffKind
from memory_engine.domain.identifiers import OwnerScope
from memory_engine.domain.vocabulary import InstructionType, SourceProcessingStatus, SourceType
from memory_engine.infrastructure.messaging import (
    ROUTES,
    CeleryPublisher,
    OutboxRelay,
    create_celery_app,
)
from memory_engine.infrastructure.object_storage import InMemoryObjectStorage
from memory_engine.infrastructure.persistence import (
    SqlAlchemyDocumentUnitOfWorkFactory,
    SqlAlchemyPersonalUnitOfWorkFactory,
)
from memory_engine.personal.application.ingestion import (
    IngestionLimits,
    IngestionRequest,
    PersonalIngestionService,
)

pytestmark = pytest.mark.integration

DEFAULT_BROKER_URL = "amqp://raven_test:raven_test_only@127.0.0.1:55672/raven_test"
T0 = datetime(2026, 11, 12, 9, 0, tzinfo=UTC)
NOW = T0 + timedelta(minutes=1)
LIMITS = IngestionLimits(
    max_text_bytes=256 * 1024, max_conversation_messages=1000, max_conversation_bytes=4 * 1024**2
)


def _broker_settings(url: str, **overrides: Any) -> BrokerSettings:
    parts = urlsplit(url)
    vhost = unquote(parts.path.lstrip("/"))
    if not vhost.endswith("_test"):
        raise RuntimeError("Broker tests only run against a virtual host whose name ends in _test")
    values: dict[str, Any] = {
        "host": parts.hostname or "127.0.0.1",
        "port": parts.port or 5672,
        "virtual_host": vhost,
        "user": unquote(parts.username or ""),
        "password": SecretStr(unquote(parts.password or "")),
        "connect_timeout_seconds": 3,
        "confirm_timeout_seconds": 5,
    }
    return BrokerSettings.model_validate(values | overrides)


@pytest.fixture(scope="session")
def broker_settings() -> BrokerSettings:
    settings = _broker_settings(os.environ.get("RAVEN_TEST_BROKER_URL", DEFAULT_BROKER_URL))
    app = create_celery_app(settings)
    try:
        with app.connection_for_write() as connection:
            connection.ensure_connection(max_retries=1)
    except Exception:
        pytest.skip("RabbitMQ test broker unreachable; run `docker compose up -d broker-test`")
    return settings


@pytest.fixture
def celery_app(broker_settings: BrokerSettings) -> Iterator[Celery]:
    app = create_celery_app(broker_settings)
    with app.connection_for_write() as connection:
        channel = connection.default_channel
        for queue in app.conf.task_queues:
            queue(channel).declare()
            queue(channel).purge()
    yield app
    app.close()


def _drain(app: Celery, kind: HandoffKind) -> list[tuple[dict[str, Any], Any]]:
    """Every message on the kind's queue, as (headers, body), acknowledged."""
    queue = next(q for q in app.conf.task_queues if q.name == ROUTES[kind].queue)
    received: list[tuple[dict[str, Any], Any]] = []
    with Connection(app.conf.broker_url) as connection:  # type: ignore[no-untyped-call]
        bound = queue(connection.default_channel)
        while (message := bound.get(no_ack=False, accept=["json"])) is not None:
            received.append((dict(message.headers), message.decode()))
            message.ack()
    return received


@pytest.fixture
def make_relay(
    session_factory: sessionmaker[Session],
) -> Iterator[Callable[..., OutboxRelay]]:
    """Relays sharing the test transaction; their publishers are closed afterwards."""
    publishers: list[CeleryPublisher] = []

    def make(publisher: CeleryPublisher, now: datetime = NOW) -> OutboxRelay:
        publishers.append(publisher)
        return OutboxRelay(
            session_factory, publisher, OutboxSettings(), clock=lambda: now, jitter=lambda d: d
        )

    yield make
    for publisher in publishers:
        publisher.close()


def _ingest_text(
    uow_factory: SqlAlchemyPersonalUnitOfWorkFactory,
    owner: OwnerScope,
    key: str,
    instruction: InstructionType = InstructionType.NORMAL,
) -> uuid.UUID:
    service = PersonalIngestionService(
        uow_factory, InMemoryObjectStorage(), LIMITS, clock=lambda: T0
    )
    return service.ingest(
        owner,
        IngestionRequest(
            owner_id=owner.owner_id,
            idempotency_key=key,
            source_type=SourceType.TEXT,
            instruction_type=instruction,
            text="Synthetic note for the broker test.",
        ),
    ).source_id


def test_registrations_reach_their_queues_as_celery_tasks(
    celery_app: Celery,
    broker_settings: BrokerSettings,
    make_relay: Callable[..., OutboxRelay],
    uow_factory: SqlAlchemyPersonalUnitOfWorkFactory,
    doc_uow_factory: SqlAlchemyDocumentUnitOfWorkFactory,
    owner: OwnerScope,
) -> None:
    source_id = _ingest_text(uow_factory, owner, "broker-1")
    forget_id = _ingest_text(uow_factory, owner, "broker-2", InstructionType.FORGET)
    document = DocumentIngestionService(
        doc_uow_factory, InMemoryObjectStorage(), max_upload_bytes=1024, clock=lambda: T0
    ).ingest(
        owner,
        DocumentUpload(
            owner_id=owner.owner_id,
            idempotency_key="broker-doc",
            filename="synthetic.txt",
            data=io.BytesIO(b"Synthetic document text."),
        ),
    )
    publisher = CeleryPublisher(
        celery_app, confirm_timeout_seconds=broker_settings.confirm_timeout_seconds
    )
    assert make_relay(publisher).relay_due().published == 2

    [(headers, body)] = _drain(celery_app, HandoffKind.PERSONAL_EXTRACTION)
    assert headers["task"] == ROUTES[HandoffKind.PERSONAL_EXTRACTION].task_name
    args, kwargs, _ = body
    envelope = HandoffEnvelope.from_dict(args[0])  # what an 8.4 worker would validate
    assert kwargs == {}
    assert headers["id"] == str(envelope.message_id)
    assert (envelope.task_id, envelope.user_id) == (source_id, owner.owner_id)
    assert envelope.task_id != forget_id  # forget never reaches extraction

    [(headers, body)] = _drain(celery_app, HandoffKind.DOCUMENT_EXTRACTION)
    envelope = HandoffEnvelope.from_dict(body[0][0])
    assert headers["task"] == ROUTES[HandoffKind.DOCUMENT_EXTRACTION].task_name
    assert envelope.task_id == document.operation_id
    assert envelope.payload["media_type"] == "text/plain"

    with uow_factory() as uow:
        queued = uow.sources.get(owner, source_id)
        forgotten = uow.sources.get(owner, forget_id)
    assert queued is not None and queued.processing_status is SourceProcessingStatus.QUEUED
    assert forgotten is not None
    assert forgotten.processing_status is SourceProcessingStatus.VALIDATED
    with doc_uow_factory() as uow:
        operation = uow.operations.get(owner, document.operation_id)
    assert operation is not None and operation.status is OperationStatus.QUEUED


def test_an_unreachable_broker_leaves_the_handoff_recoverable(
    celery_app: Celery,
    broker_settings: BrokerSettings,
    make_relay: Callable[..., OutboxRelay],
    uow_factory: SqlAlchemyPersonalUnitOfWorkFactory,
    owner: OwnerScope,
) -> None:
    source_id = _ingest_text(uow_factory, owner, "broker-down")
    # Nothing listens on port 1: every connection attempt is refused.
    down = create_celery_app(broker_settings.model_copy(update={"port": 1}))
    try:
        unreachable = CeleryPublisher(down, confirm_timeout_seconds=1)
        assert make_relay(unreachable).relay_due().retry_scheduled == 1
    finally:
        down.close()
    with uow_factory() as uow:
        source = uow.sources.get(owner, source_id)
        [message] = uow.outbox.for_subject(owner, source_id)
    assert source is not None and source.processing_status is SourceProcessingStatus.VALIDATED
    assert (message.attempts, message.last_error_code) == (1, "MESSAGE_PUBLISH_ERROR")
    assert _drain(celery_app, HandoffKind.PERSONAL_EXTRACTION) == []

    # The broker is reachable again: after the backoff the same message goes out once.
    healthy = CeleryPublisher(
        celery_app, confirm_timeout_seconds=broker_settings.confirm_timeout_seconds
    )
    assert make_relay(healthy, NOW + timedelta(seconds=10)).relay_due().published == 1
    [(headers, _)] = _drain(celery_app, HandoffKind.PERSONAL_EXTRACTION)
    assert headers["id"] == str(message.id)
    with uow_factory() as uow:
        source = uow.sources.get(owner, source_id)
    assert source is not None and source.processing_status is SourceProcessingStatus.QUEUED
