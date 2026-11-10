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


class InfrastructureError(MemoryEngineError):
    """A technical dependency (database, storage, broker, model) failed."""

    code: ClassVar[str] = "INFRASTRUCTURE_ERROR"


class PersistenceError(InfrastructureError):
    """Persisting or reading authoritative state failed."""

    code: ClassVar[str] = "PERSISTENCE_ERROR"
