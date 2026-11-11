"""Publishing handoff messages through Celery (owner-approved: ``send_task``).

Each message becomes a Celery task message whose single argument is the 7.4
envelope, with the outbox id as the Celery task id. Publisher confirms make
``publish`` return only after RabbitMQ accepted the message; anything else
raises :class:`MessagePublishError`, and the outbox keeps the message pending.
"""

from typing import Any, Protocol

from amqp.exceptions import AMQPError, MessageNacked
from celery import Celery
from kombu.exceptions import KombuError

from memory_engine.domain.handoff import OutboxMessage
from memory_engine.exceptions import MessagePublishError
from memory_engine.infrastructure.messaging.topology import EXCHANGE_NAME, ROUTES

_BROKER_ERRORS = (OSError, KombuError, AMQPError, MessageNacked)


class MessagePublisher(Protocol):
    def publish(self, message: OutboxMessage) -> None:
        """Return only once the broker confirmed the message; else raise
        :class:`MessagePublishError`."""
        ...


class CeleryPublisher:
    """Keeps one connection; drops it after any failure so the next call reconnects."""

    def __init__(self, app: Celery, *, confirm_timeout_seconds: float) -> None:
        self._app = app
        self._confirm_timeout = confirm_timeout_seconds
        self._connection: Any = None
        self._producer: Any = None

    def publish(self, message: OutboxMessage) -> None:
        route = ROUTES[message.kind]
        try:
            self._app.send_task(
                route.task_name,
                args=[message.envelope.to_dict()],
                task_id=str(message.id),
                queue=route.queue,
                exchange=EXCHANGE_NAME,
                routing_key=route.routing_key,
                producer=self._current_producer(),
                retry=False,
                confirm_timeout=self._confirm_timeout,
            )
        except _BROKER_ERRORS as err:
            self.close()
            raise MessagePublishError("the broker did not confirm the message") from err

    def _current_producer(self) -> Any:
        if self._producer is None:
            connection = self._app.connection_for_write()
            try:
                # One attempt, bounded by the connect timeout: the outbox owns retries.
                connection.ensure_connection(
                    max_retries=0,
                    interval_start=0,
                    interval_step=0,
                    timeout=self._app.conf.broker_connection_timeout,
                )
            except BaseException:
                connection.release()
                raise
            self._connection = connection
            self._producer = self._app.amqp.Producer(connection)
        return self._producer

    def close(self) -> None:
        connection, self._connection, self._producer = self._connection, None, None
        if connection is not None:
            try:
                connection.release()
            except _BROKER_ERRORS:  # already broken; nothing left to release
                return
