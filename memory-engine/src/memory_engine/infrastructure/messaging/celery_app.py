"""Celery wiring for the Memory Engine (7.4 sections 3.2 and 21; 7.1 section 24.3).

The app declares the handoff topology and safe defaults. It registers no
consumer tasks yet: extraction (plan 8.4) and the document pipeline (plan 8.12)
add theirs under the task names in :mod:`topology`.

Defaults follow 7.4: JSON only (never pickle), acknowledgement after the task
finishes (``task_acks_late``; 7.4 section 11.3), redelivery when a worker dies,
one message prefetched per worker process, publisher confirms, and no Celery
result backend: Raven's database records are the authoritative state (7.4
section 8.1).
"""

from urllib.parse import quote

from celery import Celery
from kombu.entity import Exchange, Queue

from memory_engine.config.settings import BrokerSettings
from memory_engine.infrastructure.messaging.topology import EXCHANGE_NAME, ROUTES

APP_NAME = "raven_memory_engine"


def build_broker_url(settings: BrokerSettings) -> str:
    scheme = "amqps" if settings.use_tls else "amqp"
    user = quote(settings.user, safe="")
    password = quote(settings.password.get_secret_value(), safe="")
    vhost = quote(settings.virtual_host, safe="")
    return f"{scheme}://{user}:{password}@{settings.host}:{settings.port}/{vhost}"


def handoff_queues() -> list[Queue]:
    exchange = Exchange(EXCHANGE_NAME, type="direct", durable=True)  # type: ignore[no-untyped-call]
    return [
        Queue(route.queue, exchange, routing_key=route.routing_key, durable=True)  # type: ignore[no-untyped-call]
        for route in ROUTES.values()
    ]


def create_celery_app(settings: BrokerSettings) -> Celery:
    app = Celery(APP_NAME, set_as_current=False)
    app.conf.update(
        broker_url=build_broker_url(settings),
        broker_use_ssl=settings.use_tls,
        broker_connection_timeout=settings.connect_timeout_seconds,
        broker_transport_options={"confirm_publish": True},
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        task_ignore_result=True,
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        worker_prefetch_multiplier=1,
        task_queues=handoff_queues(),
        task_create_missing_queues=False,
        task_routes={
            route.task_name: {
                "queue": route.queue,
                "exchange": EXCHANGE_NAME,
                "routing_key": route.routing_key,
            }
            for route in ROUTES.values()
        },
        # The outbox relay owns retries (bounded, with backoff); Celery must not retry.
        task_publish_retry=False,
        worker_hijack_root_logger=False,
        enable_utc=True,
        timezone="UTC",
    )
    return app
