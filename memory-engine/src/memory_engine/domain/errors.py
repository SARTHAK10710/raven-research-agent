"""Domain-layer errors: violations of business invariants.

Kept separate from infrastructure errors so that domain code never depends on
technical failure types.
"""

from typing import ClassVar

from memory_engine.exceptions.base import MemoryEngineError


class DomainError(MemoryEngineError):
    """A business rule or invariant was violated."""

    code: ClassVar[str] = "DOMAIN_ERROR"


class DomainValidationError(DomainError):
    """A domain value or state transition is invalid."""

    code: ClassVar[str] = "VALIDATION_ERROR"


class OwnershipError(DomainError):
    """An operation would cross a user-ownership boundary."""

    code: ClassVar[str] = "OWNERSHIP_VIOLATION"


__all__ = ["DomainError", "DomainValidationError", "OwnershipError"]
