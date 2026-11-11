"""Base error hierarchy for the Memory Engine.

Every error carries a stable, machine-readable ``code`` (logged as
``error_code``, Phase 7.7 section 6.1) and a *safe* message: no secrets,
credentials or raw user content. Callers preserve the original cause of a
technical failure with ``raise SomeError(...) from err`` unless the cause itself
contains unsafe data (see ``memory_engine.config.settings.load_settings``).

Feature-specific errors (ingestion, extraction, resolution, retrieval,
deletion) are added in the subphases that raise them.
"""

from collections.abc import Mapping
from typing import ClassVar


class MemoryEngineError(Exception):
    """Root of every error raised by the Memory Engine."""

    code: ClassVar[str] = "MEMORY_ENGINE_ERROR"

    def __init__(self, message: str, *, details: Mapping[str, str] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details: dict[str, str] = dict(details or {})

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


class ConfigurationError(MemoryEngineError):
    """Configuration is missing or invalid. Raised at startup."""

    code: ClassVar[str] = "CONFIGURATION_ERROR"


class ApplicationError(MemoryEngineError):
    """An application-layer use case cannot proceed."""

    code: ClassVar[str] = "APPLICATION_ERROR"


class AuthorizationError(ApplicationError):
    """The caller is not authorized to perform the requested operation."""

    code: ClassVar[str] = "AUTHORIZATION_DENIED"


class RecordNotFoundError(ApplicationError):
    """The record does not exist within the caller's owner scope.

    Raised identically for a missing record and for another owner's record, so
    the error never reveals whether a private resource exists.
    """

    code: ClassVar[str] = "RECORD_NOT_FOUND"


class DeletionInProgressError(ApplicationError):
    """The target is being deleted; derived content must not be (re)created.

    Raised so a stale worker cannot recreate content from a document whose
    deletion has been requested (memory/05 sections 18-19).
    """

    code: ClassVar[str] = "DELETION_IN_PROGRESS"


class ConcurrencyConflictError(ApplicationError):
    """An optimistic-concurrency check failed: the record changed since it was read.

    The caller may reload and retry; nothing was written (Decision 5.9.4).
    """

    code: ClassVar[str] = "CONCURRENCY_CONFLICT"


class InfrastructureError(MemoryEngineError):
    """A technical dependency (database, storage, broker, model) failed."""

    code: ClassVar[str] = "INFRASTRUCTURE_ERROR"


class PersistenceError(InfrastructureError):
    """Persisting or reading authoritative state failed."""

    code: ClassVar[str] = "PERSISTENCE_ERROR"


class ObjectStorageError(InfrastructureError):
    """Object storage is unavailable or an object operation failed (7.2 section 18).

    Nothing is guaranteed to be stored when this is raised; callers keep the
    operation in a retryable state rather than reporting success.
    """

    code: ClassVar[str] = "OBJECT_STORAGE_ERROR"


class ObjectIntegrityError(ObjectStorageError):
    """Stored bytes do not match the expected size or SHA-256 (7.2 section 10).

    The object is removed before this is raised, so corrupt content is never
    left behind under a valid key.
    """

    code: ClassVar[str] = "OBJECT_INTEGRITY_ERROR"
