"""Identifiers and ownership scope shared by both Memory Engine domains.

The Memory Engine does not authenticate users. Its callers pass a validated
:class:`OwnerScope` carrying an opaque owner identifier, and every private
record and repository operation is bound to it (Phase 7.1 section 23.4).
"""

import uuid
from dataclasses import dataclass

from memory_engine.domain.errors import DomainValidationError


def new_id() -> uuid.UUID:
    """Return a new globally unique record identifier."""
    return uuid.uuid4()


@dataclass(frozen=True, slots=True)
class OwnerScope:
    """The owner on whose behalf an operation runs.

    Holding an ``OwnerScope`` means the caller has already authenticated and
    authorized the owner; the Memory Engine only enforces that data stays
    within it.
    """

    owner_id: uuid.UUID

    def __post_init__(self) -> None:
        if not isinstance(self.owner_id, uuid.UUID):
            raise DomainValidationError("owner_id must be a UUID")
        if self.owner_id.int == 0:
            raise DomainValidationError("owner_id must not be the nil UUID")

    def owns(self, owner_id: uuid.UUID) -> bool:
        """Return True if a record with ``owner_id`` belongs to this scope."""
        return self.owner_id == owner_id
