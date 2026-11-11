"""RabbitMQ and Celery adapters for the reliable handoff (Phase 8.3 step 4; 7.4).

* :mod:`topology`: the ``raven.memory`` exchange, queues, routing keys and task names.
* :func:`create_celery_app`: Celery configured for the handoff topology.
* :class:`CeleryPublisher`: publishes one outbox message with publisher confirms.
* :class:`OutboxRelay`: moves pending ``me_outbox`` rows to the broker.
* :func:`register_extraction_task`: the Celery consumer for personal extraction (8.4).

Only this package (and the tests) import celery, kombu or amqp.
"""

from memory_engine.infrastructure.messaging.celery_app import (
    build_broker_url,
    create_celery_app,
    handoff_queues,
)
from memory_engine.infrastructure.messaging.publisher import CeleryPublisher, MessagePublisher
from memory_engine.infrastructure.messaging.relay import (
    OutboxRelay,
    RelayOutcome,
    RelayReport,
    backoff_seconds,
)
from memory_engine.infrastructure.messaging.tasks import register_extraction_task, retry_delay
from memory_engine.infrastructure.messaging.topology import EXCHANGE_NAME, ROUTES, Route

__all__ = [
    "EXCHANGE_NAME",
    "ROUTES",
    "CeleryPublisher",
    "MessagePublisher",
    "OutboxRelay",
    "RelayOutcome",
    "RelayReport",
    "Route",
    "backoff_seconds",
    "build_broker_url",
    "create_celery_app",
    "handoff_queues",
    "register_extraction_task",
    "retry_delay",
]
