"""Plan 8.1 initial test 5: exception behavior."""

import pytest

from memory_engine.domain.errors import DomainError, DomainValidationError, OwnershipError
from memory_engine.exceptions import (
    ApplicationError,
    AuthorizationError,
    ConcurrencyConflictError,
    ConfigurationError,
    InfrastructureError,
    MemoryEngineError,
    PersistenceError,
    RecordNotFoundError,
)

ALL_ERRORS: list[type[MemoryEngineError]] = [
    MemoryEngineError,
    ConfigurationError,
    ApplicationError,
    AuthorizationError,
    InfrastructureError,
    PersistenceError,
    RecordNotFoundError,
    ConcurrencyConflictError,
    DomainError,
    DomainValidationError,
    OwnershipError,
]


@pytest.mark.parametrize("error_type", ALL_ERRORS)
def test_every_error_is_a_memory_engine_error(error_type: type[MemoryEngineError]) -> None:
    assert issubclass(error_type, MemoryEngineError)


def test_error_codes_are_unique() -> None:
    codes = [error_type.code for error_type in ALL_ERRORS]
    assert len(codes) == len(set(codes))


@pytest.mark.parametrize("error_type", [DomainError, DomainValidationError, OwnershipError])
def test_domain_errors_are_separate_from_technical_errors(
    error_type: type[MemoryEngineError],
) -> None:
    assert not issubclass(error_type, InfrastructureError)
    assert not issubclass(error_type, ApplicationError)
    assert not issubclass(error_type, ConfigurationError)


@pytest.mark.parametrize("error_type", [InfrastructureError, PersistenceError])
def test_infrastructure_errors_are_not_domain_errors(error_type: type[MemoryEngineError]) -> None:
    assert not issubclass(error_type, DomainError)


def test_string_form_includes_stable_code() -> None:
    error = PersistenceError("Could not store memory source")
    assert str(error) == "[PERSISTENCE_ERROR] Could not store memory source"
    assert error.message == "Could not store memory source"


def test_details_are_copied_not_shared() -> None:
    details = {"field": "environment"}
    error = ConfigurationError("bad", details=details)
    details["field"] = "changed"
    assert error.details == {"field": "environment"}


def test_original_cause_is_preserved() -> None:
    original = OSError("disk unavailable")
    with pytest.raises(PersistenceError) as caught:
        try:
            raise original
        except OSError as err:
            raise PersistenceError("Could not persist candidate") from err

    assert caught.value.__cause__ is original


def test_errors_can_be_caught_at_the_root() -> None:
    with pytest.raises(MemoryEngineError):
        raise OwnershipError("Operation crosses a user boundary")
