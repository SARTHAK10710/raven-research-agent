"""Shared fixtures for Memory Engine tests.

All configuration values are synthetic. No test reads a developer's .env file,
touches real infrastructure, or makes network calls.
"""

import logging
import os
from collections.abc import Iterator

import pytest

from memory_engine.config import ENV_PREFIX
from memory_engine.observability import LOGGER_NAMESPACE

SYNTHETIC_PASSWORD = "synthetic-test-password-7f3a"  # noqa: S105 - test-only value
SYNTHETIC_SECRET_KEY = "synthetic-object-store-secret-9c1e"  # noqa: S105 - test-only value
SYNTHETIC_BROKER_PASSWORD = "synthetic-broker-password-4b2d"  # noqa: S105 - test-only value

VALID_ENV: dict[str, str] = {
    f"{ENV_PREFIX}ENVIRONMENT": "testing",
    f"{ENV_PREFIX}DATABASE__HOST": "db.test.invalid",
    f"{ENV_PREFIX}DATABASE__NAME": "raven_test",
    f"{ENV_PREFIX}DATABASE__USER": "raven_memory_role",
    f"{ENV_PREFIX}DATABASE__PASSWORD": SYNTHETIC_PASSWORD,
    f"{ENV_PREFIX}OBJECT_STORAGE__ENDPOINT_URL": "http://objects.test.invalid:8333",
    f"{ENV_PREFIX}OBJECT_STORAGE__BUCKET": "raven-memory",
    f"{ENV_PREFIX}OBJECT_STORAGE__ACCESS_KEY_ID": "synthetic-access-key",
    f"{ENV_PREFIX}OBJECT_STORAGE__SECRET_ACCESS_KEY": SYNTHETIC_SECRET_KEY,
    f"{ENV_PREFIX}BROKER__HOST": "broker.test.invalid",
    f"{ENV_PREFIX}BROKER__VIRTUAL_HOST": "raven_test",
    f"{ENV_PREFIX}BROKER__USER": "raven_memory_publisher",
    f"{ENV_PREFIX}BROKER__PASSWORD": SYNTHETIC_BROKER_PASSWORD,
}


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove any Memory Engine variables inherited from the developer's shell."""
    for key in list(os.environ):
        if key.upper().startswith(ENV_PREFIX):
            monkeypatch.delenv(key)


@pytest.fixture
def valid_env(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """Set a complete, valid synthetic configuration."""
    for key, value in VALID_ENV.items():
        monkeypatch.setenv(key, value)
    return dict(VALID_ENV)


@pytest.fixture
def synthetic_password() -> str:
    return SYNTHETIC_PASSWORD


@pytest.fixture
def synthetic_secret_key() -> str:
    return SYNTHETIC_SECRET_KEY


@pytest.fixture
def synthetic_broker_password() -> str:
    return SYNTHETIC_BROKER_PASSWORD


@pytest.fixture(autouse=True)
def restore_memory_engine_logger() -> Iterator[None]:
    """Undo any logger configuration a test performs."""
    logger = logging.getLogger(LOGGER_NAMESPACE)
    handlers, level, propagate = list(logger.handlers), logger.level, logger.propagate
    yield
    logger.handlers[:] = handlers
    logger.setLevel(level)
    logger.propagate = propagate
