"""Celery consumer for personal extraction handoffs (plan 8.4; owner-approved, 8.4 step 1).

The task name and queue come from :mod:`topology`. Messages are acknowledged
after the task returns (``task_acks_late``), so a worker that dies mid-task
leaves the message for redelivery; the service's atomic outcome makes the
redelivery harmless.

Retries: transient infrastructure errors (database, object storage) are
retried with exponential backoff, bounded by ``ExtractionSettings``. When the
retries run out, the source is marked ``processing_failed`` with the error
code. Everything else is decided by the service and never retried.

Known limitation: if marking the failure itself fails (the database is down
for the whole retry window), the task errors and the source stays ``queued``;
a reconciliation sweep for such sources is not built yet.
"""

from collections.abc import Callable
from typing import Any

from celery import Celery

from memory_engine.config.settings import ExtractionSettings
from memory_engine.domain.handoff import HandoffKind
from memory_engine.infrastructure.messaging.topology import ROUTES
from memory_engine.personal.application.extraction import TRANSIENT_ERRORS, ExtractionService


def retry_delay(retries: int, settings: ExtractionSettings) -> float:
    """Seconds before retry ``retries + 1``: doubling from the base, capped."""
    exponent = min(retries, 60)
    return float(
        min(settings.retry_backoff_max_seconds, settings.retry_backoff_seconds * 2**exponent)
    )


def register_extraction_task(
    app: Celery, service: Callable[[], ExtractionService], settings: ExtractionSettings
) -> Any:
    """Register the consumer on ``app``; ``service`` builds the service in the worker.

    The factory runs inside the worker process, after any fork, so database
    engines are created per process (7.1 section 23.2).
    """
    route = ROUTES[HandoffKind.PERSONAL_EXTRACTION]

    @app.task(  # type: ignore[untyped-decorator]
        name=route.task_name,
        bind=True,
        acks_late=True,
        reject_on_worker_lost=True,
        max_retries=settings.max_retries,
        ignore_result=True,
    )
    def extract_personal_source(task: Any, envelope: dict[str, Any]) -> dict[str, Any]:
        retries = int(task.request.retries)
        worker = service()
        try:
            return worker.handle(envelope, attempt=retries + 1).as_dict()
        except TRANSIENT_ERRORS as err:
            code = getattr(err, "code", "TRANSIENT_FAILURE")
            if retries >= settings.max_retries:
                return worker.mark_failed(envelope, code, attempt=retries + 1).as_dict()
            raise task.retry(exc=err, countdown=retry_delay(retries, settings)) from err

    return extract_personal_source
