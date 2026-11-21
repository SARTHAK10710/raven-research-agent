"""Broker topology for handoff messages (owner-approved, 8.3 step 4; 7.1 section 24.3).

One durable direct exchange, ``raven.memory``, and one durable queue per handoff
kind. No dead-letter queue yet: dead-letter routing and retention are settled
with the consumers (7.4 sections 13 and 22). Queue names never carry user data,
and authorization never depends on them (7.4 section 6.2).
"""

from dataclasses import dataclass
from types import MappingProxyType

from memory_engine.domain.handoff import HandoffKind

EXCHANGE_NAME = "raven.memory"


@dataclass(frozen=True, slots=True)
class Route:
    task_name: str  # the Celery task a consumer registers under this name
    queue: str
    routing_key: str


ROUTES: MappingProxyType[HandoffKind, Route] = MappingProxyType(
    {
        HandoffKind.DOCUMENT_EXTRACTION: Route(
            task_name="memory.document.extraction",
            queue="memory.document.processing",
            routing_key="document.extraction.requested",
        ),
        HandoffKind.PERSONAL_EXTRACTION: Route(
            task_name="memory.personal.extraction",
            queue="memory.personal.extraction",
            routing_key="personal.extraction.requested",
        ),
        # 8.4 step 5: the consumer (memory resolution) arrives with plan 8.6; until
        # then messages wait in this durable queue, as document handoffs wait for 8.12.
        HandoffKind.PERSONAL_RESOLUTION: Route(
            task_name="memory.personal.resolution",
            queue="memory.personal.resolution",
            routing_key="personal.resolution.requested",
        ),
    }
)
