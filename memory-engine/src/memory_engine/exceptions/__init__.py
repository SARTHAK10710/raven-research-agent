"""Structured Memory Engine errors that are not domain errors.

Domain errors live in :mod:`memory_engine.domain.errors` so the domain layer
stays independent of application and infrastructure concerns.
"""

from memory_engine.exceptions.base import (
    ApplicationError,
    AuthorizationError,
    ConcurrencyConflictError,
    ConfigurationError,
    DeletionInProgressError,
    IdempotencyKeyReusedError,
    InfrastructureError,
    IngestionRejectedError,
    MemoryEngineError,
    MessagePublishError,
    ObjectIntegrityError,
    ObjectStorageError,
    PersistenceError,
    RecordNotFoundError,
)

__all__ = [
    "ApplicationError",
    "AuthorizationError",
    "ConcurrencyConflictError",
    "ConfigurationError",
    "DeletionInProgressError",
    "IdempotencyKeyReusedError",
    "InfrastructureError",
    "IngestionRejectedError",
    "MemoryEngineError",
    "MessagePublishError",
    "ObjectIntegrityError",
    "ObjectStorageError",
    "PersistenceError",
    "RecordNotFoundError",
]
